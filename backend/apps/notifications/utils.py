import logging
from .models import Notification
from apps.accounts.models import User
from gertrack.business_rules import (
    NOTIF_TYPE_BUDGET_RAL_SEUIL, VALIDATION_TYPE_URGENT, NOTIF_TYPE_PROJECT_BUDGET_BLOQUE,
    NOTIF_TYPE_A_EXECUTER_FINANCIER, NOTIF_TYPE_EXECUTEE_FINANCIEREMENT, ROLE_FINANCIAL,
)

logger = logging.getLogger(__name__)


def _get_dg_users():
    users = User.objects.filter(role='dg', is_active=True)
    if not users.exists():
        logger.warning("[NOTIF] Aucun utilisateur DG (role='dg') trouvé.")
    return users

def _get_dop_users():
    return User.objects.filter(role='chef_ops', is_active=True)

def _get_stock_users():
    return User.objects.filter(role='stock', is_active=True)

def _get_financial_users():
    return User.objects.filter(role=ROLE_FINANCIAL, is_active=True)


def _create_notif(recipient, category, notif_type, title, message, link='', object_id=None):
    """Crée une notification, puis la pousse en temps réel (WebSocket) si le
    destinataire a une connexion active — sans jamais bloquer la création
    si la diffusion temps réel échoue ou n'est pas disponible."""
    try:
        notif = Notification.objects.create(
            recipient=recipient,
            category=category,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link,
            object_id=object_id,
        )
        logger.info(f"[NOTIF] Créée → {recipient.username} : {title}")
        _push_realtime(notif)
    except Exception as e:
        logger.error(f"[NOTIF] Erreur création pour {recipient.username} : {e}")


def _push_realtime(notif):
    """Diffuse la notification au groupe WebSocket du destinataire (best-effort)."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notif.recipient_id}',
            {
                'type': 'notify',
                'data': {
                    'id':         notif.id,
                    'category':   notif.category,
                    'notif_type': notif.notif_type,
                    'title':      notif.title,
                    'message':    notif.message,
                    'link':       notif.link,
                    'object_id':  notif.object_id,
                    'is_read':    notif.is_read,
                    'created_at': notif.created_at.isoformat(),
                },
            },
        )
    except Exception as e:
        logger.warning(f"[NOTIF] Diffusion temps réel impossible : {e}")


# ── Demandes ──────────────────────────────────────────────────────────────────

def _request_category(request_obj):
    """Catégorie de notification adaptée au type réel de la demande : 'achat'
    pour une demande d'achat, 'stock' pour un mouvement de stock (entrée,
    sortie, ajustement)."""
    return 'achat' if request_obj.request_type == 'achat' else 'stock'


def notify_demande_soumise(request_obj):
    demandeur = request_obj.requested_by.get_full_name() or request_obj.requested_by.username
    is_urgent = request_obj.validation_type == VALIDATION_TYPE_URGENT

    title   = ('[URGENT] ' if is_urgent else '') + f'Nouvelle demande : {request_obj.reference}'
    message = (
        f'{demandeur} a soumis une {request_obj.get_request_type_display()} '
        f'({request_obj.items.count()} article(s))'
    )
    if is_urgent:
        message += ' — URGENTE : le premier des deux (DOP ou DG) à statuer décide seul.'
    else:
        message += '.'
    link = '/requests'

    category = _request_category(request_obj)

    # Notifie le DOP si circuit double (dop_then_dg), OU course urgente
    # DOP/DG (Évolution 5 — les deux sont notifiés simultanément, le premier
    # à statuer l'emporte, voir UnifiedRequest._act_on_urgent).
    if request_obj.validation_type in ('dop_then_dg', VALIDATION_TYPE_URGENT):
        for user in _get_dop_users():
            _create_notif(user, category, 'demande_soumise', title, message, link, request_obj.id)

    # Toujours notifier DG
    for user in _get_dg_users():
        _create_notif(user, category, 'demande_soumise', title, message, link, request_obj.id)


def notify_demande_validee(request_obj, by_role='dg'):
    validator = None
    if by_role == 'dg' and request_obj.dg_validated_by:
        validator = request_obj.dg_validated_by.get_full_name() or request_obj.dg_validated_by.username
    elif by_role == 'dop' and request_obj.dop_validated_by:
        validator = request_obj.dop_validated_by.get_full_name() or request_obj.dop_validated_by.username

    _create_notif(
        recipient  = request_obj.requested_by,
        category   = _request_category(request_obj),
        notif_type = 'demande_validee',
        title      = f'Demande validée : {request_obj.reference}',
        message    = f'Votre demande a été validée par {validator or by_role.upper()}.',
        link       = '/requests',
        object_id  = request_obj.id,
    )


def notify_demande_refusee(request_obj, by_role='dg', comment=''):
    msg = f'Votre demande {request_obj.reference} a été refusée.'
    if comment:
        msg += f' Motif : {comment}'

    _create_notif(
        recipient  = request_obj.requested_by,
        category   = _request_category(request_obj),
        notif_type = 'demande_refusee',
        title      = f'Demande refusée : {request_obj.reference}',
        message    = msg,
        link       = '/requests',
        object_id  = request_obj.id,
    )


def notify_demande_executee(request_obj):
    recipients = list(set([request_obj.requested_by] + list(_get_stock_users())))
    for user in recipients:
        _create_notif(
            recipient  = user,
            category   = 'stock',
            notif_type = 'demande_executee',
            title      = f'Demande exécutée : {request_obj.reference}',
            message    = (
                f'Les mouvements de stock ont été créés automatiquement '
                f'suite à la validation de {request_obj.reference}.'
            ),
            link       = '/stock',
            object_id  = request_obj.id,
        )


# ── Responsable Financier (Évolution 7) ─────────────────────────────────────

def notify_a_executer_financier(request_obj):
    """Une demande d'achat vient d'être validée — notifie le Responsable
    Financier qu'elle attend son exécution (voir
    UnifiedRequest.execute_financial). Jamais envoyée pour un autre type de
    demande, ni pour les événements du circuit logistique."""
    demandeur = request_obj.requested_by.get_full_name() or request_obj.requested_by.username
    for user in _get_financial_users():
        _create_notif(
            recipient  = user,
            category   = 'achat',
            notif_type = NOTIF_TYPE_A_EXECUTER_FINANCIER,
            title      = f'Demande à exécuter : {request_obj.reference}',
            message    = f'{demandeur} a une demande d\'achat validée en attente d\'exécution.',
            link       = '/financial-execution',
            object_id  = request_obj.id,
        )


def notify_demande_executee_financierement(request_obj):
    """La demande vient d'être exécutée par le Responsable Financier — le
    demandeur et le RAL sont notifiés (le circuit logistique n'a pas encore
    commencé ; ses propres notifications — réception, retard — restent
    gérées séparément par notify_logistics_receptionnee)."""
    recipients = list(set([request_obj.requested_by] + list(_get_stock_users())))
    executant = request_obj.financial_execution_by
    executant_name = (executant.get_full_name() or executant.username) if executant else 'le Responsable Financier'
    for user in recipients:
        _create_notif(
            recipient  = user,
            category   = 'achat',
            notif_type = NOTIF_TYPE_EXECUTEE_FINANCIEREMENT,
            title      = f'Demande exécutée : {request_obj.reference}',
            message    = f'{request_obj.reference} a été exécutée par {executant_name}.',
            link       = '/requests',
            object_id  = request_obj.id,
        )


# ── Stock ─────────────────────────────────────────────────────────────────────

def notify_stock_faible(product):
    recipients = list(_get_dg_users()) + list(_get_stock_users())
    for user in recipients:
        already = Notification.objects.filter(
            recipient=user, notif_type='stock_faible',
            object_id=product.id, is_read=False,
        ).exists()
        if not already:
            _create_notif(
                recipient  = user,
                category   = 'stock',
                notif_type = 'stock_faible',
                title      = f'Stock faible : {product.code}',
                message    = (
                    f'{product.designation} — Stock actuel : {product.stock_actuel} '
                    f'(seuil : {product.stock_securite})'
                ),
                link       = '/products',
                object_id  = product.id,
            )


def notify_stock_rupture(product):
    recipients = list(_get_dg_users()) + list(_get_stock_users())
    for user in recipients:
        already = Notification.objects.filter(
            recipient=user, notif_type='stock_rupture',
            object_id=product.id, is_read=False,
        ).exists()
        if not already:
            _create_notif(
                recipient  = user,
                category   = 'stock',
                notif_type = 'stock_rupture',
                title      = f'Rupture de stock : {product.code}',
                message    = f'{product.designation} — Stock épuisé.',
                link       = '/products',
                object_id  = product.id,
            )


# ── Administration ────────────────────────────────────────────────────────────

def notify_admin_request_soumise(admin_request):
    demandeur = admin_request.requested_by.get_full_name() or admin_request.requested_by.username
    title   = f'Nouvelle demande administrative : {admin_request.reference}'
    message = f'{demandeur} a soumis une demande de type "{admin_request.get_request_type_display()}".'
    for user in _get_dg_users():
        _create_notif(user, 'systeme', 'demande_admin_soumise', title, message, '/administration', admin_request.id)


def notify_admin_request_validee(admin_request):
    _create_notif(
        recipient  = admin_request.requested_by,
        category   = 'systeme',
        notif_type = 'demande_admin_validee',
        title      = f'Demande validée : {admin_request.reference}',
        message    = f'Votre demande "{admin_request.get_request_type_display()}" a été validée par le DG.',
        link       = '/administration',
        object_id  = admin_request.id,
    )


def notify_admin_request_refusee(admin_request):
    msg = f'Votre demande {admin_request.reference} a été refusée.'
    if admin_request.review_comment:
        msg += f' Motif : {admin_request.review_comment}'
    _create_notif(
        recipient  = admin_request.requested_by,
        category   = 'systeme',
        notif_type = 'demande_admin_refusee',
        title      = f'Demande refusée : {admin_request.reference}',
        message    = msg,
        link       = '/administration',
        object_id  = admin_request.id,
    )


def notify_compte_cree(user, created_by):
    _create_notif(
        recipient  = user,
        category   = 'systeme',
        notif_type = 'compte_cree',
        title      = 'Bienvenue sur GerTrack',
        message    = f'Votre compte a été créé par {created_by.get_full_name() or created_by.username}.',
        link        = '/dashboard',
        object_id  = user.id,
    )


# ── Budget ────────────────────────────────────────────────────────────────────

def notify_budget_depasse(project, request_obj):
    recipients = list(_get_dg_users()) + list(_get_dop_users())
    for user in recipients:
        _create_notif(
            recipient  = user,
            category   = 'projet',
            notif_type = 'budget_depasse',
            title      = f'Dépassement budget : {project.name}',
            message    = (
                f'La demande {request_obj.reference} dépasse le budget du projet '
                f'{project.code}. '
                f'Budget restant : {project.budget_restant:,.0f} FCFA.'
            ),
            link       = '/requests',
            object_id  = project.id,
        )


def notify_budget_ral_seuil(budget):
    """Le budget annuel du RAL a atteint le seuil (RAL_BUDGET_BLOCK_THRESHOLD_PERCENT,
    voir gertrack.business_rules) — seul le DG peut l'augmenter ou débloquer
    le compte (voir RALBudget.is_creation_blocked)."""
    for user in _get_dg_users():
        _create_notif(
            recipient  = user,
            category   = 'systeme',
            notif_type = NOTIF_TYPE_BUDGET_RAL_SEUIL,
            title      = f'Seuil budget RAL atteint ({budget.year})',
            message    = (
                f'Le budget annuel du Responsable Achat et Logistique a atteint '
                f'{budget.pourcentage_consomme}% ({budget.montant_consomme:,.0f} / '
                f'{float(budget.montant_annuel):,.0f} FCFA). '
                f'Les nouvelles demandes d\'achat du RAL sont bloquées jusqu\'à ce '
                f'que vous augmentiez le budget ou débloquiez le compte.'
            ),
            link       = '/ral-budget',
            object_id  = budget.id,
        )


def notify_project_budget_bloque(project):
    """Le budget du projet vient d'être automatiquement bloqué (Évolution 6) :
    seuil de consommation atteint ET avancement en retard sur le dernier
    rapport hebdomadaire (voir Project.check_and_apply_budget_block). Seul
    le DG peut débloquer — voir Project.unblock_budget."""
    for user in _get_dg_users():
        _create_notif(
            recipient  = user,
            category   = 'projet',
            notif_type = NOTIF_TYPE_PROJECT_BUDGET_BLOQUE,
            title      = f'Budget projet bloqué : {project.code}',
            message    = (
                f'Le budget du projet {project.code} — {project.name} a été '
                f'automatiquement bloqué : {project.budget_pourcentage}% consommé '
                f'et avancement en retard. Plus aucune nouvelle demande ne peut y '
                f'être liée jusqu\'au déblocage manuel.'
            ),
            link       = '/operations',
            object_id  = project.id,
        )


# ── Logistique (Phase F — §7 achats / §8 sorties) ──────────────────────────────

def notify_logistics_receptionnee(request_obj, late=False):
    """Notifie la réception d'une commande (achat) ou d'une livraison chantier (sortie)."""
    if request_obj.request_type == 'achat':
        notif_type = 'commande_en_retard' if late else 'commande_arrivee'
        title      = f'Commande {"en retard" if late else "arrivée"} : {request_obj.reference}'
        message    = (
            f'La commande {request_obj.reference}'
            + (f' auprès de {request_obj.supplier.name}' if request_obj.supplier else '')
            + f' a été réceptionnée en magasin{" avec retard" if late else ""}.'
        )
        recipients = list(_get_dg_users()) + list(_get_stock_users())
        for user in recipients:
            _create_notif(user, 'achat', notif_type, title, message, '/requests', request_obj.id)

    elif request_obj.request_type == 'sortie':
        title   = f'Livraison chantier confirmée : {request_obj.reference}'
        message = f'La réception chantier de {request_obj.reference} a été confirmée' + (' avec retard.' if late else '.')
        recipients = set(list(_get_dg_users()) + list(_get_stock_users()))
        if request_obj.requested_by:
            recipients.add(request_obj.requested_by)
        for user in recipients:
            _create_notif(user, 'stock', 'livraison_chantier', title, message, '/requests', request_obj.id)


# ── Projets — échéance (Phase G — §9) ──────────────────────────────────────────

def notify_echeance_proche(project, days_remaining):
    """
    Notifie le DG et le Chef de Projet qu'un projet actif arrive à échéance.
    Appelée par la commande `check_project_deadlines` (pas de planificateur
    système dans ce projet : à exécuter quotidiennement via cron / tâche
    planifiée en production).
    """
    recipients = list(_get_dg_users())
    if project.project_manager:
        recipients.append(project.project_manager)

    for user in recipients:
        already = Notification.objects.filter(
            recipient=user, notif_type='echeance_proche',
            object_id=project.id, is_read=False,
        ).exists()
        if already:
            continue
        label = "dépassée" if days_remaining < 0 else f"dans {days_remaining} jour(s)"
        _create_notif(
            recipient  = user,
            category   = 'projet',
            notif_type = 'echeance_proche',
            title      = f'Échéance {label} : {project.name}',
            message    = (
                f'Le projet {project.code} — {project.name} arrive à échéance {label} '
                f'({project.planned_end_date.strftime("%d/%m/%Y")}).'
            ),
            link       = '/operations',
            object_id  = project.id,
        )