from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponse

from django.utils import timezone

from gertrack.business_rules import (
    ROLE_RAL, ROLE_DG, ROLE_DOP, ROLE_FINANCIAL, RAL_BUDGET_REQUEST_TYPE, REQUEST_STATUS_EXECUTED,
    VALIDATION_TYPE_URGENT, REQUEST_STATUS_AWAITING_DOP_OR_DG, URGENT_ACHAT_ALLOWED_ROLES,
)
from .models import UnifiedRequest, LogisticsStage, RALBudget, DuplicateExecutionError
from .serializers import (
    UnifiedRequestListSerializer, UnifiedRequestDetailSerializer,
    LogisticsStageSerializer, RALBudgetSerializer,
)
from .pdf_generator import generate_bon_commande
from apps.accounts.models import AuditLog
from apps.notifications.utils import (
    notify_demande_soumise,
    notify_demande_validee,
    notify_demande_refusee,
    notify_demande_executee,
    notify_budget_ral_seuil,
    notify_project_budget_bloque,
    notify_a_executer_financier,
    notify_demande_executee_financierement,
)

# ── Restrictions de types de demande par rôle ─────────────────────────────────
MAGASINIER_ALLOWED_TYPES = ('entree', 'sortie', 'ajustement')
PM_ALLOWED_TYPES          = ('entree', 'sortie')


class UnifiedRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return UnifiedRequestListSerializer
        return UnifiedRequestDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = UnifiedRequest.objects.select_related(
            'requested_by', 'warehouse', 'supplier', 'project',
            'dop_validated_by', 'dg_validated_by',
        ).prefetch_related('items__product')


        if getattr(user, 'is_dg', False) or getattr(user, 'role', '') in ('dg', 'stock'):
            pass


        elif getattr(user, 'is_ops_chief', False) or getattr(user, 'role', '') == 'chef_ops':
            # Visibilité totale (pas seulement pendant l'attente) sur les
            # demandes urgentes : le DOP est l'un des deux décideurs de la
            # course DOP/DG (Évolution 5) et doit pouvoir voir/consulter
            # l'issue même après qu'elle a été tranchée par l'autre — sans
            # quoi une tentative tardive de sa part échouerait en 404 plutôt
            # qu'un message clair "déjà tranchée" (voir validate_dop/reject_dop).
            qs = qs.filter(
                Q(requested_by=user) |
                Q(status='en_attente_dop', validation_type='dop_then_dg') |
                Q(validation_type=VALIDATION_TYPE_URGENT)
            )

        elif getattr(user, 'is_financial_officer', False) or getattr(user, 'role', '') == ROLE_FINANCIAL:
            # Responsable Financier (Évolution 7) : voit exclusivement les
            # demandes d'achat validées, en attente d'exécution — jamais les
            # commandes déjà exécutées/réceptionnées, en retard, le circuit
            # logistique, ni les entrées/sorties/ajustements. Une demande
            # disparaît de sa liste dès qu'elle est exécutée (status devient
            # 'executee', donc n'est plus 'validee' — hors de ce filtre).
            qs = qs.filter(request_type=RAL_BUDGET_REQUEST_TYPE, status='validee')

        else:
            qs = qs.filter(requested_by=user)

        
        rtype = self.request.query_params.get('type')
        if rtype:
            qs = qs.filter(request_type=rtype)

        rstatus = self.request.query_params.get('status')
        if rstatus:
            qs = qs.filter(status=rstatus)

        warehouse_id = self.request.query_params.get('warehouse')
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)

        return qs.order_by('-created_at')

    # ── Circuit de validation forcé selon le rôle du demandeur ──────────────────
    # Le magasinier n'a qu'une seule étape de validation, assurée par le
    # Responsable Achat et Logistique (jamais le DOP ni le DG). Le chef de projet passe par
    # le DOP puis par le Responsable Achat et Logistique (jamais le DG). Voir validate_dg /
    # reject_dg ci-dessous pour le choix du validateur à l'étape finale.
    def _forced_validation_type(self, user, is_urgent=False):
        # Une demande d'achat urgente (Évolution 5) impose toujours le
        # circuit de course DOP/DG, quel que soit le circuit habituel du
        # demandeur — prioritaire sur les règles ci-dessous.
        if is_urgent:
            return VALIDATION_TYPE_URGENT
        if user.role == 'magasinier':
            return 'dg_only'
        is_pm = getattr(user, 'is_project_manager', False) or user.role == 'chef_projet'
        if is_pm:
            return 'dop_then_dg'
        return None

    # ── Validateur de l'étape finale (statut 'en_attente_dg') ──────────────────
    # Pour une demande soumise par un magasinier ou un chef de projet, cette
    # étape est réservée au Responsable Achat et Logistique (jamais le DG). Pour toute autre
    # demande (soumise par le DG ou le Responsable Achat et Logistique lui-même), elle reste
    # réservée au DG.
    def _requester_is_mag_or_pm(self, instance):
        requester = instance.requested_by
        return bool(requester) and requester.role in ('magasinier', 'chef_projet')

    def _can_act_at_dg_stage(self, user, instance):
        if self._requester_is_mag_or_pm(instance):
            return user.role == 'stock'
        return getattr(user, 'is_dg', False) or user.role == 'dg'

    def _dg_stage_error(self, instance):
        if self._requester_is_mag_or_pm(instance):
            return 'Réservé au Responsable Achat et Logistique pour les demandes des magasiniers et chefs de projet.'
        return 'Réservé au DG.'

    # ── Rôles réels DOP/DG (course urgente — Évolution 5) ───────────────────
    # Contrairement au circuit habituel (où le Responsable Achat et
    # Logistique peut se substituer au DOP/DG pour certaines demandes — voir
    # _can_act_at_dg_stage), la course DOP/DG d'une demande urgente est
    # strictement réservée aux deux rôles réels : ni le RAL ni personne
    # d'autre ne peut s'y substituer.
    def _is_real_dop(self, user):
        return getattr(user, 'is_ops_chief', False) or user.role == ROLE_DOP

    def _is_real_dg(self, user):
        return getattr(user, 'is_dg', False) or user.role == ROLE_DG

    # ── Contrôle des droits par rôle sur le type de demande / magasin / projet ──
    def _enforce_role_constraints(self, user, request_type, warehouse, project, is_urgent=False):
        if project is not None and project.is_budget_blocked:
            # Budget projet bloqué automatiquement (Évolution 6) — bloque
            # toute nouvelle demande liée à ce projet, quel que soit son type
            # ou son rôle demandeur, jusqu'au déblocage manuel du DG (voir
            # Project.check_and_apply_budget_block / unblock_budget).
            AuditLog.log(
                user, AuditLog.ACTION_DENIED, 'UnifiedRequest', '',
                f"Tentative de création/modification refusée — budget du projet "
                f"{project.code} bloqué : {project.budget_block_reason}"
            )
            raise PermissionDenied(
                f"Le budget du projet {project.code} est bloqué "
                f"({project.budget_pourcentage}% consommé et avancement en retard) — "
                "aucune nouvelle demande ne peut y être liée. Contactez le DG pour débloquer."
            )

        if is_urgent:
            # Demande d'achat urgente (Évolution 5) : réservée à un
            # sous-ensemble de rôles, toujours liée à un projet — contrôlé
            # une seule fois ici, avant les restrictions habituelles
            # ci-dessous (qu'elle contourne pour le type 'achat').
            if request_type != RAL_BUDGET_REQUEST_TYPE:
                raise ValidationError({'is_urgent': ["Seule une demande d'achat peut être marquée urgente."]})
            if user.role not in URGENT_ACHAT_ALLOWED_ROLES:
                raise PermissionDenied(
                    "Seuls le Chef de Projet, le Magasinier et le Responsable Achat "
                    "et Logistique peuvent créer une demande d'achat urgente."
                )
            if project is None:
                raise ValidationError({'project': ["Un projet est obligatoire pour une demande d'achat urgente."]})

        urgent_achat = is_urgent and request_type == RAL_BUDGET_REQUEST_TYPE

        if user.role == 'magasinier':
            if not urgent_achat and request_type not in MAGASINIER_ALLOWED_TYPES:
                raise PermissionDenied(
                    "Le magasinier ne peut créer que des demandes d'entrée, de sortie, "
                    "d'ajustement, ou une demande d'achat urgente."
                )
            if warehouse is not None and warehouse.manager_id != user.id:
                raise PermissionDenied("Vous n'avez pas accès à ce magasin.")

        is_pm = getattr(user, 'is_project_manager', False) or user.role == 'chef_projet'
        if is_pm:
            if not urgent_achat and request_type not in PM_ALLOWED_TYPES:
                raise PermissionDenied(
                    "Le chef de projet ne peut créer que des demandes d'entrée, de "
                    "sortie, ou une demande d'achat urgente."
                )
            if project is None:
                raise ValidationError({'project': ["Un projet est obligatoire pour le chef de projet."]})
            if project.project_manager_id != user.id:
                raise PermissionDenied(
                    "Vous ne pouvez créer une demande que pour un projet qui vous est affecté."
                )

    def _get_ral_budget_or_raise(self, year):
        """Budget annuel RAL obligatoire pour toute demande d'achat du RAL
        (Évolution 4) — bloque aussi bien l'absence totale de budget pour
        `year` que le dépassement du seuil, afin qu'aucune demande d'achat
        ne puisse jamais exister sans budget associé et disponible."""
        budget = RALBudget.objects.filter(year=year).first()
        if budget is None:
            raise PermissionDenied(
                f"Aucun budget annuel n'a été défini pour {year} — une demande "
                "d'achat ne peut jamais être créée sans budget associé. "
                "Contactez le DG pour en créer un."
            )
        if budget.is_creation_blocked:
            raise PermissionDenied(
                f"Le budget annuel du RAL a atteint {budget.pourcentage_consomme}% — "
                "création de nouvelles demandes d'achat bloquée. Contactez le DG "
                "pour augmenter le budget ou débloquer le compte."
            )
        return budget

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'is_dg', False) or user.role == 'dg':
            raise PermissionDenied("Le DG ne peut pas créer de demande — ce rôle est réservé à la validation.")
        if getattr(user, 'is_financial_officer', False) or user.role == ROLE_FINANCIAL:
            raise PermissionDenied(
                "Le Responsable Financier ne peut pas créer de demande — ce rôle est "
                "réservé à l'exécution des demandes d'achat déjà validées."
            )

        request_type = serializer.validated_data.get('request_type')
        is_urgent    = serializer.validated_data.get('is_urgent', False)
        save_kwargs  = {'requested_by': user}
        if user.role == ROLE_RAL and request_type == RAL_BUDGET_REQUEST_TYPE:
            try:
                save_kwargs['budget'] = self._get_ral_budget_or_raise(timezone.now().year)
            except PermissionDenied as e:
                AuditLog.log(
                    user, AuditLog.ACTION_DENIED, 'UnifiedRequest', '',
                    f"Tentative de création de demande d'achat refusée — {e}"
                )
                raise

        self._enforce_role_constraints(
            user, request_type,
            serializer.validated_data.get('warehouse'),
            serializer.validated_data.get('project'),
            is_urgent,
        )
        forced = self._forced_validation_type(user, is_urgent)
        if forced:
            save_kwargs['validation_type'] = forced
        request_obj = serializer.save(**save_kwargs)
        AuditLog.log(
            user, AuditLog.ACTION_CREATE, 'UnifiedRequest', request_obj.id,
            f"Demande créée : {request_obj.reference} ({request_obj.get_request_type_display()})"
        )

    def perform_update(self, serializer):
        user         = self.request.user
        instance     = serializer.instance
        request_type = serializer.validated_data.get('request_type', instance.request_type)
        is_urgent    = serializer.validated_data.get('is_urgent', instance.is_urgent)

        save_kwargs = {}
        if user.role == ROLE_RAL and request_type == RAL_BUDGET_REQUEST_TYPE and instance.budget_id is None:
            # Le budget n'est résolu et lié qu'UNE SEULE fois — à la création,
            # ou ici si le type bascule vers 'achat' pour la première fois
            # (contournement sinon possible : créer sous un autre type, puis
            # éditer vers 'achat'). Une fois lié, `budget` est une
            # photographie figée de l'année de création : ni une nouvelle
            # édition, ni la création d'un budget pour une autre année, ni
            # une modification du montant annuel ne doivent jamais le faire
            # changer — voir UnifiedRequest.budget. La sélection se fait donc
            # sur `instance.created_at.year` (date réelle de création),
            # jamais sur `timezone.now()` (date de l'édition en cours).
            try:
                save_kwargs['budget'] = self._get_ral_budget_or_raise(instance.created_at.year)
            except PermissionDenied as e:
                AuditLog.log(
                    user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                    f"Tentative de modification de demande d'achat refusée — {instance.reference} : {e}"
                )
                raise
        elif request_type != RAL_BUDGET_REQUEST_TYPE and instance.budget_id is not None:
            # Le type n'est plus 'achat' : ce champ n'a de sens que pour les
            # achats (voir UnifiedRequest.budget).
            save_kwargs['budget'] = None

        self._enforce_role_constraints(
            user, request_type,
            serializer.validated_data.get('warehouse', instance.warehouse),
            serializer.validated_data.get('project', instance.project),
            is_urgent,
        )
        forced = self._forced_validation_type(user, is_urgent)
        if forced:
            save_kwargs['validation_type'] = forced
        old_is_urgent = instance.is_urgent
        request_obj = serializer.save(**save_kwargs)
        AuditLog.log(
            user, AuditLog.ACTION_UPDATE, 'UnifiedRequest', request_obj.id,
            f"Demande modifiée : {request_obj.reference}"
        )

        # ── Traçabilité avant/après (Évolution 8) ───────────────────────────
        # Champ métier sensible uniquement — voir
        # gertrack.business_rules.AUDIT_TRACKED_FIELDS. Événement distinct du
        # log générique ci-dessus (jamais remplacé, seulement complété).
        if request_obj.is_urgent != old_is_urgent:
            AuditLog.log(
                user, AuditLog.ACTION_UPDATE, 'UnifiedRequest', request_obj.id,
                f"Priorité de la demande {request_obj.reference} modifiée",
                field_name='is_urgent',
                old_value={'is_urgent': old_is_urgent},
                new_value={'is_urgent': request_obj.is_urgent},
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'brouillon':
            return Response(
                {'detail': 'Seul un brouillon peut être supprimé.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if instance.requested_by != request.user and request.user.role not in ('dg', 'stock'):
            return Response(
                {'detail': 'Vous ne pouvez pas supprimer cette demande.'},
                status=status.HTTP_403_FORBIDDEN
            )
        AuditLog.log(
            request.user, AuditLog.ACTION_DELETE, 'UnifiedRequest', instance.id,
            f"Demande supprimée : {instance.reference}"
        )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Soumettre ─────────────────────────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        instance = self.get_object()
        is_dg = getattr(request.user, 'is_dg', False) or request.user.role in ('dg', 'stock')

        if instance.requested_by != request.user and not is_dg:
            return Response({'detail': 'Accès refusé.'}, status=status.HTTP_403_FORBIDDEN)
        if instance.items.count() == 0:
            return Response(
                {'detail': 'Impossible de soumettre une demande sans articles.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            instance.submit()
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notify_demande_soumise(instance)
        except Exception as e:
            print(f"[NOTIF ERROR submit] {e}")

        try:
            if instance.project and instance.project.budget:
                demande_total  = float(instance.total_amount)
                budget_restant = instance.project.budget_restant or 0
                if demande_total > budget_restant:
                    from apps.notifications.utils import notify_budget_depasse
                    notify_budget_depasse(instance.project, instance)
        except Exception as e:
            print(f"[NOTIF ERROR budget] {e}")

        return Response(UnifiedRequestDetailSerializer(instance).data)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Statistiques globales des demandes selon le rôle."""
        user = request.user
        qs   = UnifiedRequest.objects.all()

        # Filtre selon le rôle
        if not (getattr(user, 'is_dg', False) or user.role in ('dg', 'stock')):
            if user.role == 'chef_ops':
                qs = qs.filter(
                    Q(requested_by=user) |
                    Q(status__in=['en_attente_dop', 'en_attente_dg', 'validee', 'refusee', 'executee'])
                )
            else:
                qs = qs.filter(requested_by=user)

        return Response({
            'total':         qs.count(),
            'brouillon':     qs.filter(status='brouillon').count(),
            'en_attente_dop':qs.filter(status='en_attente_dop').count(),
            'en_attente_dg': qs.filter(status='en_attente_dg').count(),
            'en_attente_dop_dg': qs.filter(status=REQUEST_STATUS_AWAITING_DOP_OR_DG).count(),
            'validee':       qs.filter(status='validee').count(),
            'executee':      qs.filter(status='executee').count(),
            'refusee':       qs.filter(status='refusee').count(),
            # Par type
            'achat':         qs.filter(request_type='achat').count(),
            'entree':        qs.filter(request_type='entree').count(),
            'sortie':        qs.filter(request_type='sortie').count(),
            'ajustement':    qs.filter(request_type='ajustement').count(),
        })


    @action(detail=True, methods=['post'], url_path='validate-dop')
    def validate_dop(self, request, pk=None):
        instance = self.get_object()

        if instance.validation_type == VALIDATION_TYPE_URGENT:
            if not self._is_real_dop(request.user):
                return Response({'detail': 'Réservé au DOP pour une demande urgente.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            is_dop   = self._is_real_dop(request.user)
            is_stock = request.user.role == 'stock'
            if not (is_dop or is_stock):
                return Response({'detail': 'Réservé au DOP ou au Responsable Achat et Logistique.'}, status=status.HTTP_403_FORBIDDEN)

        comment = request.data.get('comment', '')

        try:
            instance.validate_dop(request.user, comment)
        except DuplicateExecutionError as e:
            # Traçabilité uniquement — pas de notification : soit un
            # double-clic/retry (circuit normal), soit la course urgente déjà
            # tranchée par le DG (voir UnifiedRequest._act_on_urgent).
            AuditLog.log(
                request.user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                f"Tentative de validation DOP refusée — {instance.reference} : {e}"
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_VALIDATE, 'UnifiedRequest', instance.id,
            f"Demande {instance.reference} validée (étape DOP)"
        )
        try:
            notify_demande_validee(instance, by_role='dop')
            # Course urgente uniquement : le DOP peut ici finaliser
            # directement la demande à 'validee' (voir _act_on_urgent) — le
            # circuit classique dop_then_dg passe par 'en_attente_dg' et
            # n'atteint jamais 'validee' à cette étape.
            self._notify_financial_officer_if_achat_validated(instance)
        except Exception as e:
            print(f"[NOTIF ERROR validate_dop] {e}")

        return Response(UnifiedRequestDetailSerializer(instance).data)


    @action(detail=True, methods=['post'], url_path='reject-dop')
    def reject_dop(self, request, pk=None):
        instance = self.get_object()

        if instance.validation_type == VALIDATION_TYPE_URGENT:
            if not self._is_real_dop(request.user):
                return Response({'detail': 'Réservé au DOP pour une demande urgente.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            is_dop   = self._is_real_dop(request.user)
            is_stock = request.user.role == 'stock'
            if not (is_dop or is_stock):
                return Response({'detail': 'Réservé au DOP ou au Responsable Achat et Logistique.'}, status=status.HTTP_403_FORBIDDEN)

        comment = request.data.get('comment', '')

        try:
            instance.reject_dop(request.user, comment)
        except DuplicateExecutionError as e:
            AuditLog.log(
                request.user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                f"Tentative de refus DOP refusée — {instance.reference} : {e}"
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_REFUSE, 'UnifiedRequest', instance.id,
            f"Demande {instance.reference} refusée (étape DOP) — {comment}"
        )
        try:
            notify_demande_refusee(instance, by_role='dop', comment=comment)
        except Exception as e:
            print(f"[NOTIF ERROR reject_dop] {e}")

        return Response(UnifiedRequestDetailSerializer(instance).data)


    @action(detail=True, methods=['post'], url_path='validate-dg')
    def validate_dg(self, request, pk=None):
        instance = self.get_object()

        if instance.validation_type == VALIDATION_TYPE_URGENT:
            if not self._is_real_dg(request.user):
                return Response({'detail': 'Réservé au DG pour une demande urgente.'}, status=status.HTTP_403_FORBIDDEN)
        elif not self._can_act_at_dg_stage(request.user, instance):
            return Response({'detail': self._dg_stage_error(instance)}, status=status.HTTP_403_FORBIDDEN)

        comment  = request.data.get('comment', '')

        try:
            instance.validate_dg(request.user, comment)
        except DuplicateExecutionError as e:
            # Traçabilité uniquement — pas de notification, ce n'est pas un
            # refus métier mais une tentative bloquée par une garde technique
            # (double-clic, retry, appel concurrent).
            AuditLog.log(
                request.user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                f"Tentative de validation DG refusée — {instance.reference} : {e}"
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_VALIDATE, 'UnifiedRequest', instance.id,
            f"Demande {instance.reference} validée (étape DG) — statut : {instance.status}"
        )
        try:
            notify_demande_validee(instance, by_role='dg')
            if instance.status == 'executee':
                notify_demande_executee(instance)
            # Achat validé (Évolution 7) : notifie le Responsable Financier —
            # ni le budget RAL ni le budget projet ne sont jamais consommés à
            # la simple validation (voir RALBudget.montant_consomme,
            # Project.budget_consomme) — seule l'exécution financière
            # déclenche désormais ces vérifications (voir execute_financial).
            self._notify_financial_officer_if_achat_validated(instance)
        except Exception as e:
            print(f"[NOTIF ERROR validate_dg] {e}")

        return Response(UnifiedRequestDetailSerializer(instance).data)

    def _notify_financial_officer_if_achat_validated(self, instance):
        """Une demande d'achat vient d'atteindre 'validee' (circuit classique
        ou course urgente) — notifie le Responsable Financier qu'une nouvelle
        demande attend son exécution (Évolution 7)."""
        if instance.request_type != RAL_BUDGET_REQUEST_TYPE or instance.status != 'validee':
            return
        notify_a_executer_financier(instance)

    def _check_project_budget_block(self, instance, user):
        """Après exécution financière d'une demande d'achat liée à un projet
        (Évolution 7 : c'est désormais à l'exécution, jamais à la simple
        validation, que le budget projet est réellement consommé — voir
        Project.budget_consomme), le budget du projet peut avoir franchi le
        seuil de blocage automatique (Évolution 6) — voir
        Project.check_and_apply_budget_block. Ne fait rien si la demande
        n'est pas 'executee', n'est pas un achat, ou n'est liée à aucun
        projet."""
        if instance.request_type != RAL_BUDGET_REQUEST_TYPE or instance.status != REQUEST_STATUS_EXECUTED or not instance.project:
            return
        project = instance.project
        if project.check_and_apply_budget_block():
            AuditLog.log(
                user, AuditLog.ACTION_UPDATE, 'Project', project.id,
                f"Budget projet {project.code} bloqué automatiquement — {project.budget_block_reason}"
            )
            try:
                notify_project_budget_bloque(project)
            except Exception as e:
                print(f"[NOTIF ERROR project_budget_block] {e}")

    def _check_ral_budget_threshold(self, instance):
        """Après exécution financière réelle d'une demande d'achat du RAL
        (voir execute_financial), notifie le DG si le budget annuel vient
        d'atteindre 85% (une seule fois par franchissement). Une simple
        validation ne déclenche jamais ce contrôle : voir
        RALBudget.montant_consomme."""
        if instance.request_type != RAL_BUDGET_REQUEST_TYPE or instance.status != REQUEST_STATUS_EXECUTED:
            return
        requester = instance.requested_by
        if not requester or requester.role != ROLE_RAL:
            return
        try:
            budget = RALBudget.objects.filter(year=instance.created_at.year).first()
            if budget and budget.is_threshold_reached and not budget.threshold_notified_at:
                notify_budget_ral_seuil(budget)
                budget.threshold_notified_at = timezone.now()
                budget.save(update_fields=['threshold_notified_at'])
        except Exception as e:
            print(f"[NOTIF ERROR ral_budget_threshold] {e}")


    @action(detail=True, methods=['post'], url_path='reject-dg')
    def reject_dg(self, request, pk=None):
        instance = self.get_object()

        if instance.validation_type == VALIDATION_TYPE_URGENT:
            if not self._is_real_dg(request.user):
                return Response({'detail': 'Réservé au DG pour une demande urgente.'}, status=status.HTTP_403_FORBIDDEN)
        elif not self._can_act_at_dg_stage(request.user, instance):
            return Response({'detail': self._dg_stage_error(instance)}, status=status.HTTP_403_FORBIDDEN)

        comment  = request.data.get('comment', '')

        try:
            instance.reject_dg(request.user, comment)
        except DuplicateExecutionError as e:
            AuditLog.log(
                request.user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                f"Tentative de refus DG refusée — {instance.reference} : {e}"
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_REFUSE, 'UnifiedRequest', instance.id,
            f"Demande {instance.reference} refusée (étape DG) — {comment}"
        )
        try:
            notify_demande_refusee(instance, by_role='dg', comment=comment)
        except Exception as e:
            print(f"[NOTIF ERROR reject_dg] {e}")

        return Response(UnifiedRequestDetailSerializer(instance).data)

    # ── Compteur en attente ───────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='pending-count')
    def pending_count(self, request):
        user = request.user
        qs   = UnifiedRequest.objects.all()

        mag_or_pm = Q(requested_by__role__in=['magasinier', 'chef_projet'])
        if getattr(user, 'role', '') == 'stock':
            # Le Responsable Achat et Logistique ne valide que les demandes de magasinier/chef
            # de projet arrivées à l'étape finale (voir _can_act_at_dg_stage).
            count = qs.filter(status='en_attente_dg').filter(mag_or_pm).count()
        elif getattr(user, 'is_dg', False) or getattr(user, 'role', '') == 'dg':
            # Le DG valide l'étape finale de toute demande SAUF celles des
            # magasiniers/chefs de projet (réservées au Responsable Achat et Logistique),
            # plus les demandes urgentes en course DOP/DG (Évolution 5).
            count = (
                qs.filter(status='en_attente_dg').exclude(mag_or_pm).count()
                + qs.filter(status=REQUEST_STATUS_AWAITING_DOP_OR_DG).count()
            )
        elif getattr(user, 'is_ops_chief', False) or getattr(user, 'role', '') == 'chef_ops':
            count = (
                qs.filter(status='en_attente_dop', validation_type='dop_then_dg').count()
                + qs.filter(status=REQUEST_STATUS_AWAITING_DOP_OR_DG).count()
            )
        elif getattr(user, 'is_financial_officer', False) or getattr(user, 'role', '') == ROLE_FINANCIAL:
            # Achats validés en attente d'exécution financière (Évolution 7).
            count = qs.filter(status='validee', request_type=RAL_BUDGET_REQUEST_TYPE).count()
        else:
            count = qs.filter(
                requested_by=user,
                status__in=['en_attente_dop', 'en_attente_dg']
            ).count()
        return Response({'pending': count})

    # ── Responsable Financier — dashboard et historique dédiés (audit
    # UX/Évolution 7) — réutilise UnifiedRequestListSerializer et la
    # pagination standard, comme le reste du module.
    def _check_financial_officer(self, user):
        if not (getattr(user, 'is_financial_officer', False) or user.role == ROLE_FINANCIAL):
            raise PermissionDenied("Réservé au Responsable Financier.")

    @action(detail=False, methods=['get'], url_path='financial-dashboard')
    def financial_dashboard(self, request):
        self._check_financial_officer(request.user)
        user = request.user
        today = timezone.now().date()

        to_execute_qs = UnifiedRequest.objects.filter(
            request_type=RAL_BUDGET_REQUEST_TYPE, status='validee',
        ).prefetch_related('items')
        executed_by_me = UnifiedRequest.objects.filter(
            request_type=RAL_BUDGET_REQUEST_TYPE, status=REQUEST_STATUS_EXECUTED,
            financial_execution_by=user,
        )

        return Response({
            'to_execute_count':          to_execute_qs.count(),
            'to_execute_total_value':    float(sum(r.total_amount for r in to_execute_qs)),
            'urgent_count':              to_execute_qs.filter(is_urgent=True).count(),
            'executed_today_count':      executed_by_me.filter(financial_execution_at__date=today).count(),
            'executed_this_month_count': executed_by_me.filter(
                financial_execution_at__year=today.year, financial_execution_at__month=today.month,
            ).count(),
        })

    @action(detail=False, methods=['get'], url_path='financial-history')
    def financial_history(self, request):
        """Historique des achats exécutés par CE Responsable Financier —
        jamais les réceptions/retards/clôtures (voir logistics_status, non
        exposé ici) : uniquement le fait qu'il les a exécutés."""
        self._check_financial_officer(request.user)
        qs = UnifiedRequest.objects.filter(
            request_type=RAL_BUDGET_REQUEST_TYPE,
            status=REQUEST_STATUS_EXECUTED,
            financial_execution_by=request.user,
        ).select_related('requested_by', 'project', 'supplier').prefetch_related('items').order_by('-financial_execution_at')

        page = self.paginate_queryset(qs)
        serializer = UnifiedRequestListSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # ── Budget projet (NOUVEAU) ───────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='project-budget')
    def project_budget(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'detail': 'project_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            from apps.operations.models import Project
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response(
                {'detail': 'Projet introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response({
            'project_id':         project.id,
            'project_name':       project.name,
            'budget_alloue':      float(project.budget) if project.budget else None,
            'budget_consomme':    project.budget_consomme,
            'budget_restant':     project.budget_restant,
            'budget_depasse':     project.budget_depasse,
            'budget_pourcentage': project.budget_pourcentage,
        })

    # ── Circuit logistique (Phase F — §7 achats / §8 sorties) ─────────────────
    @action(detail=True, methods=['post'], url_path='advance-logistics')
    def advance_logistics(self, request, pk=None):
        instance = self.get_object()

        if not LogisticsStage.objects.filter(request_type=instance.request_type, is_active=True).exists():
            return Response(
                {'detail': "Aucun circuit logistique n'est configuré pour ce type de demande."},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = request.data.get('logistics_status')
        if not new_status:
            return Response({'detail': 'logistics_status est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        is_dg        = getattr(request.user, 'is_dg', False) or request.user.role == 'dg'
        is_requester = instance.requested_by_id == request.user.id

        reception_stage = instance._logistics_reception_stage
        if instance.request_type == 'sortie' and new_status == reception_stage:
            if instance.project is not None:
                # La réception chantier doit être confirmée par le Chef de
                # Projet du projet concerné — ni le Responsable Achat et Logistique, ni le DOP.
                is_project_cp = instance.project.project_manager_id == request.user.id
                if not (is_project_cp or is_dg):
                    return Response(
                        {'detail': 'Seul le Chef de Projet du projet concerné peut confirmer la réception chantier.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif not (is_requester or is_dg):
                # Sortie sans chantier/projet associé (ex. mouvement interne
                # d'un magasinier) : personne d'autre que le demandeur n'a de
                # légitimité à confirmer la réception — sans ce cas, la
                # demande restait bloquée indéfiniment (aucun Chef de Projet
                # à qui déléguer l'étape).
                return Response(
                    {'detail': "Seul l'auteur de la demande peut confirmer la réception pour une sortie sans projet associé."},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif not is_requester:
            # Le suivi logistique (commande envoyée, expédition, etc.) est
            # géré par l'auteur de la demande — pas par un rôle générique.
            return Response(
                {'detail': "Seul l'auteur de la demande peut faire avancer le circuit logistique."},
                status=status.HTTP_403_FORBIDDEN
            )

        date_prevue = request.data.get('date_livraison_prevue')

        try:
            was_late = instance.advance_logistics(new_status, request.user, date_livraison_prevue=date_prevue)
        except DuplicateExecutionError as e:
            # Traçabilité uniquement — pas de notification, ce n'est pas un
            # refus métier mais une tentative bloquée par une garde technique
            # (double-clic, retry, appel concurrent).
            AuditLog.log(
                request.user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                f"Tentative d'avancement du circuit logistique refusée — {instance.reference} : {e}"
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_UPDATE, 'UnifiedRequest', instance.id,
            f"Demande {instance.reference} — circuit logistique : {instance.logistics_status_label}"
            + (" (en retard)" if was_late else "")
        )

        try:
            if new_status == reception_stage:
                from apps.notifications.utils import notify_logistics_receptionnee
                notify_logistics_receptionnee(instance, late=was_late)
        except Exception as e:
            print(f"[NOTIF ERROR advance_logistics] {e}")

        # Pas de vérification de seuil budgétaire ici (Évolution 7) : pour un
        # achat, `status` est déjà 'executee' bien avant la réception —
        # depuis l'exécution financière (voir execute_financial ci-dessous),
        # seul moment où la consommation change réellement.

        return Response(UnifiedRequestDetailSerializer(instance).data)

    # ── Exécution financière (Évolution 7) ─────────────────────────────────
    @action(detail=True, methods=['post'], url_path='execute-financial')
    def execute_financial(self, request, pk=None):
        instance = self.get_object()

        is_financial = getattr(request.user, 'is_financial_officer', False) or request.user.role == ROLE_FINANCIAL
        if not is_financial:
            return Response(
                {'detail': 'Réservé au Responsable Financier.'}, status=status.HTTP_403_FORBIDDEN
            )

        notes = request.data.get('notes', '')

        try:
            instance.execute_financial(request.user, notes)
        except DuplicateExecutionError as e:
            # Traçabilité uniquement — pas de notification, ce n'est pas un
            # refus métier mais une tentative bloquée par une garde technique
            # (double-clic, retry, appel concurrent) — même pattern que
            # validate_dg/advance_logistics.
            AuditLog.log(
                request.user, AuditLog.ACTION_DENIED, 'UnifiedRequest', instance.id,
                f"Tentative d'exécution financière refusée — {instance.reference} : {e}"
            )
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            request.user, AuditLog.ACTION_EXECUTE, 'UnifiedRequest', instance.id,
            f"Demande {instance.reference} exécutée financièrement"
        )
        try:
            notify_demande_executee_financierement(instance)
        except Exception as e:
            print(f"[NOTIF ERROR execute_financial] {e}")

        # C'est ici, et seulement ici, que le budget (RAL ou projet) peut
        # avoir été réellement consommé pour cette demande (Évolution 7) —
        # voir RALBudget.montant_consomme / Project.budget_consomme, tous
        # deux désormais basés exclusivement sur status='executee'.
        self._check_ral_budget_threshold(instance)
        self._check_project_budget_block(instance, request.user)

        return Response(UnifiedRequestDetailSerializer(instance).data)

    # ── PDF ───────────────────────────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        instance = self.get_object()
        if instance.request_type != 'achat':
            return Response(
                {'detail': "Le PDF (Bon de commande) n'est disponible que pour les demandes d'achat."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if instance.status not in ('validee', 'executee'):
            return Response(
                {'detail': 'PDF disponible uniquement pour les demandes validées ou exécutées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            buffer   = generate_bon_commande(instance)
            filename = f'BC_{instance.reference}.pdf'
            response = HttpResponse(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {'detail': f'Erreur génération PDF : {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='pdf-preview')
    def preview_pdf(self, request, pk=None):
        instance = self.get_object()
        if instance.request_type != 'achat':
            return Response(
                {'detail': "Le PDF (Bon de commande) n'est disponible que pour les demandes d'achat."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if instance.status not in ('validee', 'executee'):
            return Response(
                {'detail': 'PDF disponible uniquement pour les demandes validées ou exécutées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            buffer   = generate_bon_commande(instance)
            filename = f'BC_{instance.reference}.pdf'
            response = HttpResponse(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {'detail': f'Erreur génération PDF : {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ─────────────────────────────────────────────────────────────────────────────
# CIRCUIT LOGISTIQUE — gestion des étapes (Responsable Achat et Logistique)
#
# Seul le RAL peut créer, modifier, supprimer, activer/désactiver et
# réordonner les étapes du circuit logistique — aucun autre profil, DG
# compris, ne peut y toucher. Le circuit de VALIDATION (UnifiedRequest.status)
# reste totalement indépendant et n'est jamais concerné par ce ViewSet.
# ─────────────────────────────────────────────────────────────────────────────
class LogisticsStageViewSet(viewsets.ModelViewSet):
    queryset           = LogisticsStage.objects.all().order_by('request_type', 'order', 'id')
    serializer_class    = LogisticsStageSerializer
    permission_classes = [IsAuthenticated]

    def _is_ral(self, user):
        return getattr(user, 'is_stock_manager', False) or user.role == ROLE_RAL

    def _check_ral(self, request):
        if not self._is_ral(request.user):
            raise PermissionDenied(
                "Seul le Responsable Achat et Logistique peut gérer le circuit logistique."
            )

    def get_queryset(self):
        self._check_ral(self.request)
        qs = super().get_queryset()
        request_type = self.request.query_params.get('request_type')
        if request_type:
            qs = qs.filter(request_type=request_type)
        return qs

    def _clear_exclusive_flags(self, request_type, field, exclude_pk=None):
        """Une seule étape active peut porter le drapeau `field` (réception
        ou clôture) par type de demande : on le retire des autres plutôt que
        de bloquer avec une erreur — plus simple à utiliser pour le RAL."""
        qs = LogisticsStage.objects.filter(request_type=request_type, **{field: True})
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        qs.update(**{field: False})

    def perform_create(self, serializer):
        self._check_ral(self.request)
        instance = serializer.save()
        if instance.is_reception_stage:
            self._clear_exclusive_flags(instance.request_type, 'is_reception_stage', instance.pk)
        if instance.is_closing_stage:
            self._clear_exclusive_flags(instance.request_type, 'is_closing_stage', instance.pk)
        AuditLog.log(
            self.request.user, AuditLog.ACTION_CREATE, 'LogisticsStage', instance.id,
            f"Étape logistique créée : [{instance.get_request_type_display()}] {instance.label}"
        )

    def perform_update(self, serializer):
        self._check_ral(self.request)
        instance = serializer.save()
        if instance.is_reception_stage:
            self._clear_exclusive_flags(instance.request_type, 'is_reception_stage', instance.pk)
        if instance.is_closing_stage:
            self._clear_exclusive_flags(instance.request_type, 'is_closing_stage', instance.pk)
        AuditLog.log(
            self.request.user, AuditLog.ACTION_UPDATE, 'LogisticsStage', instance.id,
            f"Étape logistique modifiée : [{instance.get_request_type_display()}] {instance.label}"
        )

    def perform_destroy(self, instance):
        self._check_ral(self.request)
        in_use = UnifiedRequest.objects.filter(
            request_type=instance.request_type, logistics_status=instance.code
        ).exists()
        if in_use:
            raise ValidationError(
                "Cette étape est utilisée par au moins une demande en cours — "
                "désactivez-la plutôt que de la supprimer."
            )
        AuditLog.log(
            self.request.user, AuditLog.ACTION_DELETE, 'LogisticsStage', instance.id,
            f"Étape logistique supprimée : [{instance.get_request_type_display()}] {instance.label}"
        )
        instance.delete()

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        self._check_ral(request)
        request_type = request.data.get('request_type')
        stage_ids    = request.data.get('stage_ids')
        if not request_type or not isinstance(stage_ids, list):
            return Response(
                {'detail': 'request_type et stage_ids (liste ordonnée d\'identifiants) sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        stages = {s.id: s for s in LogisticsStage.objects.filter(request_type=request_type, id__in=stage_ids)}
        if len(stages) != len(stage_ids) or len(set(stage_ids)) != len(stage_ids):
            return Response(
                {'detail': "stage_ids doit contenir, une seule fois chacun, tous les identifiants du circuit."},
                status=status.HTTP_400_BAD_REQUEST
            )
        for index, stage_id in enumerate(stage_ids):
            stage = stages[stage_id]
            if stage.order != index:
                stage.order = index
                stage.save(update_fields=['order', 'updated_at'])
        AuditLog.log(
            request.user, AuditLog.ACTION_UPDATE, 'LogisticsStage', '',
            f"Circuit logistique réordonné : [{request_type}]"
        )
        return Response(LogisticsStageSerializer(
            LogisticsStage.objects.filter(request_type=request_type).order_by('order', 'id'), many=True
        ).data)


# ─────────────────────────────────────────────────────────────────────────────
# BUDGET ANNUEL DU RAL — créé/modifié exclusivement par le DG
#
# Visible uniquement par le RAL et le DG. Le RAL ne peut jamais le modifier —
# lecture seule pour lui, écriture totale réservée au DG.
# ─────────────────────────────────────────────────────────────────────────────
class RALBudgetViewSet(viewsets.ModelViewSet):
    queryset           = RALBudget.objects.all().order_by('-year')
    serializer_class    = RALBudgetSerializer
    permission_classes = [IsAuthenticated]

    def _is_dg(self, user):
        return getattr(user, 'is_dg', False) or user.role == ROLE_DG

    def _is_ral(self, user):
        return getattr(user, 'is_stock_manager', False) or user.role == ROLE_RAL

    def get_queryset(self):
        user = self.request.user
        if not (self._is_dg(user) or self._is_ral(user)):
            return RALBudget.objects.none()
        qs = super().get_queryset()
        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(year=year)
        return qs

    def _check_dg(self, request):
        if not self._is_dg(request.user):
            raise PermissionDenied("Seul le DG peut gérer le budget annuel du RAL.")

    def perform_create(self, serializer):
        self._check_dg(self.request)
        instance = serializer.save(created_by=self.request.user)
        AuditLog.log(
            self.request.user, AuditLog.ACTION_CREATE, 'RALBudget', instance.id,
            f"Budget RAL créé : {instance.year} — {instance.montant_annuel} FCFA"
        )

    def perform_update(self, serializer):
        self._check_dg(self.request)
        old_montant = serializer.instance.montant_annuel
        instance = serializer.save()
        AuditLog.log(
            self.request.user, AuditLog.ACTION_UPDATE, 'RALBudget', instance.id,
            f"Budget RAL {instance.year} modifié : {old_montant} → {instance.montant_annuel} FCFA",
            # Traçabilité avant/après (Évolution 8) — voir
            # gertrack.business_rules.AUDIT_TRACKED_FIELDS. Réutilise
            # old_montant, déjà capturé ci-dessus pour la description.
            field_name='montant_annuel',
            old_value={'montant_annuel': float(old_montant) if old_montant is not None else None},
            new_value={'montant_annuel': float(instance.montant_annuel) if instance.montant_annuel is not None else None},
        )

    def perform_destroy(self, instance):
        self._check_dg(self.request)
        if instance.requests.exists():
            raise ValidationError(
                "Ce budget est utilisé par au moins une demande d'achat — "
                "suppression impossible (voir UnifiedRequest.budget). "
                "Conservez-le pour la traçabilité, ou modifiez le montant plutôt "
                "que de le supprimer."
            )
        AuditLog.log(
            self.request.user, AuditLog.ACTION_DELETE, 'RALBudget', instance.id,
            f"Budget RAL {instance.year} supprimé"
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='unblock')
    def unblock(self, request, pk=None):
        self._check_dg(request)
        instance = self.get_object()
        instance.is_manually_unblocked = True
        instance.save(update_fields=['is_manually_unblocked', 'updated_at'])
        AuditLog.log(
            request.user, AuditLog.ACTION_UPDATE, 'RALBudget', instance.id,
            f"Budget RAL {instance.year} débloqué manuellement"
        )
        return Response(RALBudgetSerializer(instance).data)