import csv
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User, AuditLog, AdminRequest
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    AuditLogSerializer,
    AdminRequestSerializer,
    ProjectManagerSerializer,
    MagasinierAccountSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login — retourne access + refresh + infos user"""
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    Trace la déconnexion dans le journal d'activité. Les tokens JWT ne sont
    pas invalidés côté serveur (pas de liste noire configurée) : le client
    supprime ses tokens localement comme aujourd'hui, cet appel ne fait
    qu'enregistrer l'événement pour la traçabilité (§6).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        AuditLog.log(
            request.user, AuditLog.ACTION_LOGOUT, 'User', request.user.id,
            f"Déconnexion de {request.user.username}"
        )
        return Response({'detail': 'Déconnexion enregistrée.'})


class ProfileView(generics.RetrieveUpdateAPIView):
    """Consulter et modifier son propre profil"""
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AuditLogListView(generics.ListAPIView):
    """Historique des actions (DG voit tout, autres voient les leurs)"""
    serializer_class   = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_dg:
            return AuditLog.objects.all()
        return AuditLog.objects.filter(user=self.request.user)


# ─────────────────────────────────────────────────────────────────────────────
# CENTRE D'AUDIT (Évolution 8) — recherche/filtres/export sur AuditLog,
# scopé par rôle. Endpoint ADDITIF : n'affecte jamais AuditLogListView ni
# ProjectManagerViewSet.activity / MagasinierAccountViewSet.activity
# ci-dessus, qui continuent de fonctionner à l'identique (voir conception
# validée — aucun remplacement).
# ─────────────────────────────────────────────────────────────────────────────

def _audit_center_queryset(user):
    """Périmètre par rôle : le DG voit tout ; les autres rôles voient leurs
    propres actions PLUS les événements touchant les objets dont ils sont
    responsables (son propre périmètre, jamais celui des autres) — même
    principe que UnifiedRequestViewSet.get_queryset et les `.activity`
    existants, juste décliné sur AuditLog plutôt que sur un seul modèle."""
    qs = AuditLog.objects.select_related('user')

    if user.is_dg:
        return qs

    own_actions = Q(user=user)

    if user.is_project_manager:
        from apps.operations.models import Project, WeeklyReport
        from apps.requests.models import UnifiedRequest
        project_ids = list(Project.objects.filter(project_manager=user).values_list('id', flat=True))
        str_ids     = [str(i) for i in project_ids]
        request_ids = [str(i) for i in UnifiedRequest.objects.filter(project_id__in=project_ids).values_list('id', flat=True)]
        report_ids  = [str(i) for i in WeeklyReport.objects.filter(project_id__in=project_ids).values_list('id', flat=True)]
        return qs.filter(
            own_actions
            | Q(model_name='Project', object_id__in=str_ids)
            | Q(model_name='UnifiedRequest', object_id__in=request_ids)
            | Q(model_name='WeeklyReport', object_id__in=report_ids)
        )

    if user.is_magasinier:
        from apps.stock.models import Warehouse
        from apps.requests.models import UnifiedRequest
        warehouse = Warehouse.objects.filter(manager=user).first()
        if warehouse is None:
            return qs.filter(own_actions)
        request_ids = [str(i) for i in UnifiedRequest.objects.filter(warehouse=warehouse).values_list('id', flat=True)]
        return qs.filter(
            own_actions
            | Q(model_name='Warehouse', object_id=str(warehouse.id))
            | Q(model_name='UnifiedRequest', object_id__in=request_ids)
        )

    if user.is_financial_officer:
        # Ne voit que ses propres exécutions financières — jamais les autres
        # types d'événements, exactement la règle déjà en vigueur depuis
        # l'Évolution 7 (voir UnifiedRequestViewSet.get_queryset).
        from apps.requests.models import UnifiedRequest
        request_ids = [str(i) for i in UnifiedRequest.objects.filter(financial_execution_by=user).values_list('id', flat=True)]
        return qs.filter(own_actions | Q(model_name='UnifiedRequest', object_id__in=request_ids))

    # DOP, RAL et tout autre rôle non explicitement scopé ci-dessus : même
    # défaut que AuditLogListView aujourd'hui — uniquement ses propres actions.
    return qs.filter(own_actions)


def _apply_audit_filters(qs, params):
    """Filtres serveur pour le Centre d'audit — jamais de filtrage côté
    client uniquement (voir contrainte de performance validée)."""
    user_id = params.get('user')
    if user_id:
        qs = qs.filter(user_id=user_id)

    model_name = params.get('model_name')
    if model_name:
        qs = qs.filter(model_name=model_name)

    action_filter = params.get('action')
    if action_filter:
        qs = qs.filter(action=action_filter)

    object_id = params.get('object_id')
    if object_id:
        qs = qs.filter(object_id=str(object_id))

    date_from = params.get('date_from')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = params.get('date_to')
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    search = params.get('search')
    if search:
        qs = qs.filter(
            Q(description__icontains=search)
            | Q(model_name__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
        )

    return qs.order_by('-created_at')


class AuditCenterViewSet(viewsets.ReadOnlyModelViewSet):
    """Centre d'audit (Évolution 8) : recherche, filtres serveur et export
    sur AuditLog, scopé par rôle (voir _audit_center_queryset). Lecture
    seule — la création d'AuditLog reste exclusivement via AuditLog.log()."""
    serializer_class   = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = _audit_center_queryset(self.request.user)
        return _apply_audit_filters(qs, self.request.query_params)

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        qs = self.get_queryset()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="audit.csv"'
        # BOM UTF-8 : sans lui, Excel sous Windows devine à tort du
        # Windows-1252 et affiche les accents comme du charabia ("ModÃ¨le").
        response.write('﻿')
        writer = csv.writer(response)
        writer.writerow(['Date', 'Utilisateur', 'Action', 'Modèle', 'Objet', 'Description', 'Champ', 'Ancienne valeur', 'Nouvelle valeur'])
        for e in qs:
            writer.writerow([
                e.created_at.strftime('%d/%m/%Y %H:%M'),
                (e.user.get_full_name() or e.user.username) if e.user else '',
                e.get_action_display(),
                e.model_name,
                e.object_id,
                e.description,
                e.field_name,
                e.old_value or '',
                e.new_value or '',
            ])
        return response

    @action(detail=False, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request):
        from .pdf_generator import generate_audit_pdf
        qs = self.get_queryset()[:500]  # évite un PDF de plusieurs milliers de lignes
        buffer = generate_audit_pdf(qs, title="Centre d'audit — Export")
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="audit.pdf"'
        return response


# ─────────────────────────────────────────────────────────────────────────────
# DEMANDES ADMINISTRATIVES
#
# Point d'entrée unique pour les demandes de création/suppression de
# ressources devant être validées par le DG (création de magasin par le
# Responsable Achat et Logistique, pour l'instant — extensible aux futurs types).
# ─────────────────────────────────────────────────────────────────────────────

# Rôles autorisés à soumettre chaque type de demande
_REQUESTER_ROLES_BY_TYPE = {
    AdminRequest.TYPE_WAREHOUSE_CREATION: ('stock',),
    AdminRequest.TYPE_WAREHOUSE_DELETION: ('stock',),
    AdminRequest.TYPE_PM_CREATION:        ('chef_ops',),
    AdminRequest.TYPE_PM_DELETION:        ('chef_ops',),
}

# Types de demande dont l'approbation nécessite un mot de passe fourni par le
# DG à cet instant précis. La création de magasin n'en fait plus partie : le
# mot de passe du compte est désormais défini par le Responsable Achat et Logistique dès
# la soumission de la demande (haché immédiatement, voir AdminRequestSerializer).
_ACCOUNT_CREATION_TYPES = (AdminRequest.TYPE_PM_CREATION, AdminRequest.TYPE_WAREHOUSE_CREATION)


class AdminRequestViewSet(viewsets.ModelViewSet):
    serializer_class   = AdminRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'post', 'head', 'options']  # pas de modification/suppression directe

    def get_queryset(self):
        user = self.request.user
        qs   = AdminRequest.objects.select_related('requested_by', 'reviewed_by')
        if user.is_dg:
            return qs.order_by('-created_at')
        return qs.filter(requested_by=user).order_by('-created_at')

    def perform_create(self, serializer):
        user         = self.request.user
        request_type = serializer.validated_data.get('request_type')
        allowed      = _REQUESTER_ROLES_BY_TYPE.get(request_type, ())
        if user.role not in allowed:
            raise PermissionDenied(
                "Vous n'êtes pas autorisé à soumettre ce type de demande."
            )
        instance = serializer.save(requested_by=user)
        AuditLog.log(
            user, AuditLog.ACTION_CREATE, 'AdminRequest', instance.id,
            f"Demande administrative créée : {instance.reference} ({instance.get_request_type_display()})"
        )
        try:
            from apps.notifications.utils import notify_admin_request_soumise
            notify_admin_request_soumise(instance)
        except Exception as e:
            print(f"[NOTIF ERROR admin_request soumise] {e}")

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        if not request.user.is_dg:
            return Response({'detail': 'Réservé au DG.'}, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        comment  = request.data.get('comment', '')
        extra    = {}

        if instance.request_type in _ACCOUNT_CREATION_TYPES:
            password = request.data.get('password', '')
            if not password or len(password) < 6:
                return Response(
                    {'detail': 'Un mot de passe (6 caractères minimum) est requis pour valider la création du compte.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            extra['password'] = password

        try:
            instance.approve(request.user, comment, **extra)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_VALIDATE, 'AdminRequest', instance.id,
            f"Demande {instance.reference} validée — {instance.result_model} #{instance.result_object_id} créé"
        )
        try:
            from apps.notifications.utils import notify_admin_request_validee, notify_compte_cree
            notify_admin_request_validee(instance)

            new_account = None
            if instance.result_model == 'User':
                new_account = User.objects.filter(pk=instance.result_object_id).first()
            elif instance.result_model == 'Warehouse':
                from apps.stock.models import Warehouse
                warehouse = Warehouse.objects.filter(pk=instance.result_object_id).first()
                new_account = warehouse.manager if warehouse else None
            if new_account:
                notify_compte_cree(new_account, request.user)
        except Exception as e:
            print(f"[NOTIF ERROR admin_request approve] {e}")

        return Response(AdminRequestSerializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        if not request.user.is_dg:
            return Response({'detail': 'Réservé au DG.'}, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        comment  = request.data.get('comment', '')

        try:
            instance.reject(request.user, comment)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_REFUSE, 'AdminRequest', instance.id,
            f"Demande {instance.reference} refusée — {comment}"
        )
        try:
            from apps.notifications.utils import notify_admin_request_refusee
            notify_admin_request_refusee(instance)
        except Exception as e:
            print(f"[NOTIF ERROR admin_request reject] {e}")

        return Response(AdminRequestSerializer(instance).data)


# ─────────────────────────────────────────────────────────────────────────────
# COMPTES CHEF DE PROJET
#
# Gestion directe des comptes (hors workflow de demande) : le DOP peut créer
# une demande (ci-dessus) et modifier un compte existant ; le DG peut créer
# directement, modifier, désactiver/réactiver et supprimer définitivement.
# ─────────────────────────────────────────────────────────────────────────────

class ProjectManagerViewSet(viewsets.ModelViewSet):
    serializer_class   = ProjectManagerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _is_dg(self, user):
        return getattr(user, 'is_dg', False) or user.role == 'dg'

    def _is_dop(self, user):
        return getattr(user, 'is_ops_chief', False) or user.role == 'chef_ops'

    def get_queryset(self):
        user = self.request.user
        if not (self._is_dg(user) or self._is_dop(user)):
            return User.objects.none()
        return User.objects.filter(role=User.ROLE_PM).order_by('first_name', 'last_name', 'username')

    def perform_create(self, serializer):
        # Création directe réservée au DG — le DOP passe par une AdminRequest.
        if not self._is_dg(self.request.user):
            raise PermissionDenied(
                "Seul le DG peut créer un compte chef de projet directement. Le DOP doit "
                "soumettre une demande via /api/accounts/admin-requests/."
            )
        instance = serializer.save()
        AuditLog.log(
            self.request.user, AuditLog.ACTION_CREATE, 'User', instance.id,
            f"Compte chef de projet créé : {instance.username}"
        )

    def perform_update(self, serializer):
        user = self.request.user
        if not (self._is_dg(user) or self._is_dop(user)):
            raise PermissionDenied("Seul le DG ou le DOP peut modifier un compte chef de projet.")
        if serializer.validated_data.get('password') and not self._is_dg(user):
            raise PermissionDenied("Seul le DG peut modifier le mot de passe d'un chef de projet.")
        instance = serializer.save()
        AuditLog.log(
            user, AuditLog.ACTION_UPDATE, 'User', instance.id,
            f"Compte chef de projet modifié : {instance.username}"
        )

    def destroy(self, request, *args, **kwargs):
        if not self._is_dg(request.user):
            return Response(
                {'detail': 'Seul le DG peut supprimer définitivement un compte chef de projet.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        username = instance.username
        instance.delete()
        AuditLog.log(
            request.user, AuditLog.ACTION_DELETE, 'User', None,
            f"Compte chef de projet supprimé définitivement : {username}"
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        if not self._is_dg(request.user):
            return Response({'detail': 'Seul le DG peut désactiver un compte.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        AuditLog.log(request.user, AuditLog.ACTION_UPDATE, 'User', instance.id, f"Compte désactivé : {instance.username}")
        return Response(ProjectManagerSerializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        if not self._is_dg(request.user):
            return Response({'detail': 'Seul le DG peut réactiver un compte.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        AuditLog.log(request.user, AuditLog.ACTION_UPDATE, 'User', instance.id, f"Compte réactivé : {instance.username}")
        return Response(ProjectManagerSerializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        if not self._is_dg(request.user):
            return Response({'detail': 'Seul le DG peut réinitialiser un mot de passe.'}, status=status.HTTP_403_FORBIDDEN)
        password = request.data.get('password', '')
        if not password or len(password) < 6:
            return Response({'detail': 'Un mot de passe de 6 caractères minimum est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        instance = self.get_object()
        instance.set_password(password)
        instance.save(update_fields=['password'])
        AuditLog.log(request.user, AuditLog.ACTION_UPDATE, 'User', instance.id, f"Mot de passe réinitialisé : {instance.username}")
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})

    @action(detail=True, methods=['get'], url_path='activity')
    def activity(self, request, pk=None):
        """Historique d'activité du chef de projet : projets, tâches récentes, reportings, demandes."""
        from apps.operations.models import Project, Task, WeeklyReport
        from apps.operations.serializers import ProjectSerializer
        from apps.requests.models import UnifiedRequest
        from apps.requests.serializers import UnifiedRequestListSerializer

        instance = self.get_object()
        projects = Project.objects.filter(project_manager=instance).select_related(
            'project_manager', 'validated_by'
        ).order_by('-created_at')

        tasks = Task.objects.filter(
            project__in=projects, is_active=True
        ).select_related('project').order_by('-updated_at')[:20]
        taches_recentes = [{
            'id': t.id, 'project_code': t.project.code, 'project_name': t.project.name,
            'name': t.name, 'task_progress': t.task_progress, 'updated_at': t.updated_at,
        } for t in tasks]

        reports = WeeklyReport.objects.filter(project__in=projects).select_related('project').order_by('-year', '-week_number')[:20]
        reportings = [{
            'id': r.id, 'project_code': r.project.code, 'project_name': r.project.name,
            'week_number': r.week_number, 'year': r.year, 'weather': r.weather,
            'summary': r.summary, 'problems': r.problems, 'progress_gap': r.progress_gap,
            'report_date': r.report_date,
        } for r in reports]

        demandes = UnifiedRequest.objects.filter(requested_by=instance).select_related(
            'requested_by', 'warehouse', 'supplier', 'project'
        ).prefetch_related('items').order_by('-created_at')[:20]

        return Response({
            'projets':          ProjectSerializer(projects, many=True).data,
            'taches_recentes':  taches_recentes,
            'reportings':       reportings,
            'demandes':         UnifiedRequestListSerializer(demandes, many=True).data,
        })


# ─────────────────────────────────────────────────────────────────────────────
# COMPTES MAGASINIER — Administration > Comptes (vue miroir)
#
# Chaque magasin possède obligatoirement son propre compte de connexion : il
# ne peut plus être créé indépendamment d'un magasin (la création se fait
# uniquement via Gestion des Magasins ou la demande de création de magasin
# validée par le DG). Ce ViewSet reste disponible en second point d'accès
# pour consulter/gérer un compte existant : modification des informations du
# gérant et de l'identifiant, réinitialisation de mot de passe,
# désactivation/réactivation et suppression définitive — chaque action reste
# synchronisée avec le magasin associé (voir WarehouseViewSet, qui offre les
# mêmes actions côté magasin).
# ─────────────────────────────────────────────────────────────────────────────

class MagasinierAccountViewSet(viewsets.ModelViewSet):
    serializer_class   = MagasinierAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _is_dg(self, user):
        return getattr(user, 'is_dg', False) or user.role == 'dg'

    def get_queryset(self):
        if not self._is_dg(self.request.user):
            return User.objects.none()
        return User.objects.filter(role=User.ROLE_MAGASINIER).order_by('first_name', 'last_name', 'username')

    def create(self, request, *args, **kwargs):
        # Pas de création indépendante : un compte magasinier n'existe que
        # rattaché à un magasin (voir Gestion des Magasins / AdminRequest).
        return Response(
            {'detail': "Un compte magasinier ne peut plus être créé indépendamment : "
                       "créez-le depuis Gestion des Magasins (avec le magasin) ou via "
                       "une demande de création de magasin."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def perform_update(self, serializer):
        if not self._is_dg(self.request.user):
            raise PermissionDenied("Seul le DG peut modifier un compte magasinier.")
        instance = serializer.save()
        AuditLog.log(
            self.request.user, AuditLog.ACTION_UPDATE, 'User', instance.id,
            f"Compte magasinier modifié : {instance.username}"
        )

    def destroy(self, request, *args, **kwargs):
        """
        Suppression définitive du compte ET du magasin associé (un magasin
        ne peut pas exister sans compte) — même comportement que
        WarehouseViewSet.delete_permanently, déclenché depuis l'autre écran.
        """
        if not self._is_dg(request.user):
            return Response(
                {'detail': 'Seul le DG peut supprimer définitivement un compte magasinier.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance  = self.get_object()
        username  = instance.username
        warehouse = instance.managed_warehouses.first()
        warehouse_label = f"{warehouse.code} — {warehouse.name}" if warehouse else None

        with transaction.atomic():
            if warehouse:
                warehouse.delete()
            instance.delete()

        AuditLog.log(
            request.user, AuditLog.ACTION_DELETE, 'User', None,
            f"Compte magasinier supprimé définitivement : {username}"
            + (f" (et le magasin {warehouse_label})" if warehouse_label else "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        if not self._is_dg(request.user):
            return Response({'detail': 'Seul le DG peut désactiver un compte.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        warehouse = instance.managed_warehouses.first()
        if warehouse:
            warehouse.is_active = False
            warehouse.save(update_fields=['is_active', 'updated_at'])
        AuditLog.log(request.user, AuditLog.ACTION_UPDATE, 'User', instance.id, f"Compte désactivé : {instance.username}")
        return Response(MagasinierAccountSerializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        if not self._is_dg(request.user):
            return Response({'detail': 'Seul le DG peut réactiver un compte.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        warehouse = instance.managed_warehouses.first()
        if warehouse:
            warehouse.is_active = True
            warehouse.save(update_fields=['is_active', 'updated_at'])
        AuditLog.log(request.user, AuditLog.ACTION_UPDATE, 'User', instance.id, f"Compte réactivé : {instance.username}")
        return Response(MagasinierAccountSerializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        if not self._is_dg(request.user):
            return Response({'detail': 'Seul le DG peut réinitialiser un mot de passe.'}, status=status.HTTP_403_FORBIDDEN)
        password = request.data.get('password', '')
        if not password or len(password) < 6:
            return Response({'detail': 'Un mot de passe de 6 caractères minimum est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        instance = self.get_object()
        instance.set_password(password)
        instance.save(update_fields=['password'])
        AuditLog.log(request.user, AuditLog.ACTION_UPDATE, 'User', instance.id, f"Mot de passe réinitialisé (magasinier) : {instance.username}")
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})

    @action(detail=True, methods=['get'], url_path='activity')
    def activity(self, request, pk=None):
        """Historique d'activité du magasinier : entrées / sorties / ajustements."""
        from apps.requests.models import UnifiedRequest
        from apps.requests.serializers import UnifiedRequestListSerializer

        instance = self.get_object()
        qs = UnifiedRequest.objects.filter(requested_by=instance).select_related(
            'requested_by', 'warehouse', 'supplier', 'project'
        ).prefetch_related('items').order_by('-created_at')

        return Response({
            'entrees':     UnifiedRequestListSerializer(qs.filter(request_type='entree')[:20], many=True).data,
            'sorties':     UnifiedRequestListSerializer(qs.filter(request_type='sortie')[:20], many=True).data,
            'ajustements': UnifiedRequestListSerializer(qs.filter(request_type='ajustement')[:20], many=True).data,
        })