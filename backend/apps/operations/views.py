from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.http import HttpResponse

from .models import Project, Task, WeeklyReport
from .serializers import (
    ProjectSerializer,
    TaskSerializer, TaskListSerializer,
    WeeklyReportSerializer, WeeklyReportListSerializer,
)
from .pdf_generator import generate_weekly_synthesis_pdf
from apps.accounts.models import AuditLog, User
from apps.notifications.utils import notify_project_budget_bloque


def _check_project_budget_block(project, user):
    """Après un nouveau rapport hebdomadaire, l'avancement peut désormais
    être en retard sur le dernier point — le budget du projet peut avoir
    franchi le seuil de blocage automatique (Évolution 6). Réutilise
    exactement la même logique que côté demandes d'achat (voir
    apps.requests.views.UnifiedRequestViewSet._check_project_budget_block) :
    seul le déclencheur diffère (ici un rapport, là une validation d'achat)."""
    if project.check_and_apply_budget_block():
        AuditLog.log(
            user, AuditLog.ACTION_UPDATE, 'Project', project.id,
            f"Budget projet {project.code} bloqué automatiquement — {project.budget_block_reason}"
        )
        try:
            notify_project_budget_bloque(project)
        except Exception as e:
            print(f"[NOTIF ERROR project_budget_block] {e}")


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class   = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'validated_by_dg']
    search_fields      = ['code', 'name', 'client', 'location']
    ordering_fields    = ['code', 'name', 'created_at', 'start_date']

    def get_queryset(self):
        qs   = Project.objects.select_related(
            'project_manager', 'validated_by', 'created_by'
        ).prefetch_related('tasks')
        user = self.request.user
        # Le Responsable Financier n'a rien à faire dans la gestion de
        # projets (Évolution 7 — audit UX/sécurité) : il voit uniquement le
        # nom du projet sur SES demandes à exécuter, via
        # UnifiedRequestListSerializer.project_name, jamais ce module.
        if user.is_stock_manager or user.is_magasinier or user.is_financial_officer:
            return qs.none()
        if user.is_project_manager:
            return qs.filter(project_manager=user)
        return qs

    def perform_create(self, serializer):
        if not self.request.user.is_ops_chief:
            raise PermissionDenied("Seul le Chef des Opérations peut créer un projet.")
        project = serializer.save(created_by=self.request.user, status='brouillon')
        AuditLog.log(
            self.request.user, AuditLog.ACTION_CREATE,
            'Project', project.id,
            f"Projet créé : {project.code} — {project.name}"
        )

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_project_manager or user.is_stock_manager:
            raise PermissionDenied("Vous n'avez pas la permission de modifier ce projet.")

        instance   = serializer.instance
        old_budget = instance.budget
        old_pm     = instance.project_manager

        project = serializer.save()
        AuditLog.log(
            user, AuditLog.ACTION_UPDATE,
            'Project', project.id,
            f"Projet modifié : {project.code}"
        )

        # ── Traçabilité avant/après (Évolution 8) ───────────────────────────
        # Champs métier sensibles uniquement — voir
        # gertrack.business_rules.AUDIT_TRACKED_FIELDS. Événements distincts
        # du log générique ci-dessus (jamais remplacé, seulement complété).
        if project.budget != old_budget:
            AuditLog.log(
                user, AuditLog.ACTION_UPDATE, 'Project', project.id,
                f"Budget du projet {project.code} modifié",
                field_name='budget',
                old_value={'budget': float(old_budget) if old_budget is not None else None},
                new_value={'budget': float(project.budget) if project.budget is not None else None},
            )
        if project.project_manager_id != (old_pm.id if old_pm else None):
            def _pm_label(u):
                return (u.get_full_name() or u.username) if u else None
            AuditLog.log(
                user, AuditLog.ACTION_UPDATE, 'Project', project.id,
                f"Chef de projet du projet {project.code} modifié",
                field_name='project_manager',
                old_value={'project_manager': _pm_label(old_pm)},
                new_value={'project_manager': _pm_label(project.project_manager)},
            )

    def perform_destroy(self, instance):
        if not self.request.user.is_ops_chief:
            raise PermissionDenied("Seul le Chef des Opérations peut supprimer un projet.")
        AuditLog.log(
            self.request.user, AuditLog.ACTION_DELETE,
            'Project', instance.id,
            f"Projet supprimé : {instance.code}"
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='validate')
    def validate_project(self, request, pk=None):
        if not request.user.is_dg:
            return Response(
                {'detail': 'Seul le Directeur Général peut valider un projet.'},
                status=status.HTTP_403_FORBIDDEN
            )
        project = self.get_object()
        project.validated_by_dg = True
        project.validated_by    = request.user
        project.validated_at    = timezone.now()
        project.status          = Project.STATUS_ACTIVE
        project.save()
        AuditLog.log(
            request.user, AuditLog.ACTION_VALIDATE,
            'Project', project.id,
            f"Projet validé par le DG : {project.code}"
        )
        return Response({'detail': f"Projet {project.code} validé.", 'status': project.status})

    @action(detail=True, methods=['post'], url_path='validate-planning')
    def validate_planning(self, request, pk=None):
        if not (request.user.is_ops_chief or request.user.is_dg):
            return Response(
                {'detail': 'Seul le Chef des Opérations ou le DG peut valider le planning.'},
                status=status.HTTP_403_FORBIDDEN
            )
        project = self.get_object()
        project.planning_validated    = True
        project.planning_validated_by = request.user
        project.planning_validated_at = timezone.now()
        project.save()
        AuditLog.log(
            request.user, AuditLog.ACTION_VALIDATE,
            'Project', project.id,
            f"Planning validé : {project.code}"
        )
        return Response({'detail': 'Planning validé.'})

    @action(detail=True, methods=['get'], url_path='tasks')
    def get_tasks(self, request, pk=None):
        project = self.get_object()
        tasks   = project.tasks.filter(is_active=True).order_by('order', 'id')
        return Response(TaskListSerializer(tasks, many=True).data)

    @action(detail=True, methods=['get'], url_path='reports')
    def get_reports(self, request, pk=None):
        project = self.get_object()
        reports = project.weekly_reports.order_by('-year', '-week_number')
        return Response(WeeklyReportListSerializer(reports, many=True).data)

    @action(detail=True, methods=['post'], url_path='weekly-report')
    def create_weekly_report(self, request, pk=None):
        project = self.get_object()
        if not request.user.is_project_manager or project.project_manager_id != request.user.id:
            raise PermissionDenied("Seul le Chef de Projet assigné peut créer un rapport pour ce projet.")
        data    = request.data.copy()
        data['project'] = project.id
        task_details = data.get('task_details', [])
        cleaned = []
        for d in task_details:
            item = dict(d)
            if isinstance(item.get('task'), dict):
                item['task'] = item['task']['id']
            cleaned.append(item)
        data['task_details'] = cleaned
        serializer = WeeklyReportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(created_by=request.user)
        AuditLog.log(
            request.user, AuditLog.ACTION_CREATE,
            'WeeklyReport', report.id,
            f"Rapport S{report.week_number}/{report.year} — {project.code}"
        )
        _check_project_budget_block(project, request.user)
        return Response(
            WeeklyReportSerializer(report).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            'total':     qs.count(),
            'en_cours':  qs.filter(status='en_cours').count(),
            'termine':   qs.filter(status='termine').count(),
            'suspendu':  qs.filter(status='suspendu').count(),
            'brouillon': qs.filter(status='brouillon').count(),
        })
    
    @action(detail=False, methods=['get'], url_path='select-list')
    def select_list(self, request):
        """
        Liste simplifiée pour les selects frontend.
        Accessible à tous les rôles authentifiés — un chef de projet ne voit
        que les projets qui lui sont affectés (project_manager).
        """
        qs = Project.objects.filter(status__in=['en_cours', 'brouillon'])
        user = request.user
        if getattr(user, 'is_project_manager', False) or user.role == 'chef_projet':
            qs = qs.filter(project_manager=user)
        projects = qs.values('id', 'code', 'name', 'budget').order_by('code')
        return Response(list(projects))

    @action(detail=False, methods=['get'], url_path='users')
    def get_users(self, request):
        users = User.objects.filter(
            is_active=True, role=User.ROLE_PM
        ).order_by('first_name', 'last_name', 'username')
        return Response([
            {
                'id':        u.id,
                'username':  u.username,
                'full_name': u.get_full_name() or u.username,
            }
            for u in users
        ])

    @action(detail=True, methods=['post'], url_path='unblock-budget')
    def unblock_budget(self, request, pk=None):
        """Débloque manuellement le budget d'un projet auto-bloqué
        (Évolution 6) — réservé au DG, seul rôle habilité à lever ce
        blocage (voir Project.unblock_budget / check_and_apply_budget_block)."""
        if not request.user.is_dg:
            return Response(
                {'detail': 'Seul le Directeur Général peut débloquer le budget d\'un projet.'},
                status=status.HTTP_403_FORBIDDEN
            )
        project = self.get_object()
        if not project.is_budget_blocked:
            return Response({'detail': "Ce projet n'est pas bloqué."}, status=status.HTTP_400_BAD_REQUEST)
        project.unblock_budget(request.user)
        AuditLog.log(
            request.user, AuditLog.ACTION_UPDATE, 'Project', project.id,
            f"Budget projet {project.code} débloqué manuellement par le DG"
        )
        return Response(ProjectSerializer(project).data)

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        projects = self.get_queryset().filter(status__in=[
            Project.STATUS_ACTIVE, Project.STATUS_ON_HOLD, Project.STATUS_DRAFT
        ])
        data = []
        for p in projects:
            last_report = p.weekly_reports.order_by('-year', '-week_number').first()
            data.append({
                'id':                   p.id,
                'code':                 p.code,
                'name':                 p.name,
                'client':               p.client,
                'status':               p.status,
                'global_progress':      p.global_progress,
                'project_manager_name': (
                    p.project_manager.get_full_name() or p.project_manager.username
                ) if p.project_manager else None,
                'planned_end_date': p.planned_end_date,
                'is_on_schedule':   p.is_on_schedule,
                'budget_depasse':   p.budget_depasse,
                'last_report': {
                    'week_number':       last_report.week_number,
                    'year':              last_report.year,
                    'weather':           last_report.weather,
                    'progress_gap':      last_report.progress_gap,
                    'delay_gap_days':    last_report.delay_gap_days,
                    'decision_expected': last_report.decision_expected,
                    'report_date':       str(last_report.report_date),
                } if last_report else None,
            })
        weather_priority = {'critique': 0, 'risque': 1, 'ok': 2, None: 3}
        data.sort(key=lambda x: weather_priority.get(
            x['last_report']['weather'] if x['last_report'] else None, 3
        ))
        alerts = [
            d for d in data
            if d['last_report'] and (
                d['last_report']['weather'] in ['risque', 'critique']
                or d['last_report']['progress_gap'] < 0
            )
        ]
        return Response({
            'projects': data,
            'alerts':   alerts,
            'summary': {
                'total':       len(data),
                'on_schedule': sum(1 for d in data if d['is_on_schedule']),
                'delayed':     sum(1 for d in data if d['is_on_schedule'] is False),
                'critical':    sum(1 for d in data if d['last_report'] and d['last_report']['weather'] == 'critique'),
                'risk':        sum(1 for d in data if d['last_report'] and d['last_report']['weather'] == 'risque'),
            }
        })


class TaskViewSet(viewsets.ModelViewSet):
    queryset           = Task.objects.select_related('project', 'responsible').filter(is_active=True)
    serializer_class   = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['project', 'is_active']
    search_fields      = ['name', 'description']

    def get_queryset(self):
        # Responsable Financier : hors périmètre (gestion de projets).
        if self.request.user.is_financial_officer:
            return Task.objects.none()
        return super().get_queryset()

    def perform_create(self, serializer):
        if not self.request.user.is_project_manager:
            raise PermissionDenied("Seul le Chef de Projet peut créer des tâches.")
        task = serializer.save()
        AuditLog.log(
            self.request.user, AuditLog.ACTION_CREATE,
            'Task', task.id,
            f"Tâche ajoutée : {task.name} — Projet {task.project.code}"
        )

    def perform_update(self, serializer):
        if not self.request.user.is_project_manager:
            raise PermissionDenied("Seul le Chef de Projet peut modifier des tâches.")
        task = serializer.save()
        AuditLog.log(
            self.request.user, AuditLog.ACTION_UPDATE,
            'Task', task.id,
            f"Tâche modifiée : {task.name}"
        )

    def perform_destroy(self, instance):
        if not self.request.user.is_project_manager:
            raise PermissionDenied("Seul le Chef de Projet peut supprimer des tâches.")
        AuditLog.log(
            self.request.user, AuditLog.ACTION_DELETE,
            'Task', instance.id,
            f"Tâche supprimée : {instance.name}"
        )
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['patch'], url_path='update-quantity')
    def update_quantity(self, request, pk=None):
        if not request.user.is_project_manager:
            return Response({'detail': 'Permission refusée.'}, status=403)
        task     = self.get_object()
        quantity = request.data.get('realized_quantity')
        if quantity is None:
            return Response({'detail': 'realized_quantity est requis.'}, status=400)
        quantity = float(quantity)
        if quantity < 0:
            return Response({'detail': 'La quantité ne peut pas être négative.'}, status=400)
        if quantity > float(task.total_quantity):
            return Response({'detail': 'Dépasse la quantité totale.'}, status=400)
        task.realized_quantity = quantity
        task.save(update_fields=['realized_quantity', 'updated_at'])
        return Response({
            'task_progress':     task.task_progress,
            'weighted_progress': task.weighted_progress,
            'realized_quantity': float(task.realized_quantity),
            'global_progress':   task.project.global_progress,
        })


class WeeklyReportViewSet(viewsets.ModelViewSet):
    queryset = WeeklyReport.objects.select_related(
        'project', 'created_by'
    ).prefetch_related('task_details')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['project', 'year', 'week_number', 'weather']
    ordering_fields    = ['year', 'week_number', 'report_date']

    def get_queryset(self):
        # Responsable Financier : hors périmètre (gestion de projets).
        if self.request.user.is_financial_officer:
            return WeeklyReport.objects.none()
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return WeeklyReportListSerializer
        return WeeklyReportSerializer

    def perform_create(self, serializer):
        if not self.request.user.is_project_manager:
            raise PermissionDenied("Seul le Chef de Projet peut créer des rapports.")
        report = serializer.save(created_by=self.request.user)
        _check_project_budget_block(report.project, self.request.user)

    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        report   = self.get_object()
        buffer   = generate_weekly_synthesis_pdf(report)
        filename = f"Rapport_{report.project.code}_S{report.week_number}_{report.year}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response