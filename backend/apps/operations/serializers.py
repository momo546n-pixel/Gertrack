from rest_framework import serializers
from .models import Project, Task, WeeklyReport, WeeklyTaskDetail


class TaskSerializer(serializers.ModelSerializer):
    task_progress      = serializers.ReadOnlyField()
    weighted_progress  = serializers.ReadOnlyField()
    remaining_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = Task
        fields = [
            'id', 'project', 'order', 'name', 'sub_activity', 'description',
            'comment', 'unit',
            'total_quantity', 'realized_quantity', 'weight',
            'planned_start', 'planned_end', 'responsible',
            'is_active', 'task_progress', 'weighted_progress',
            'remaining_quantity', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_weight(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le poids doit être entre 0 et 100.")
        return value

    def validate_total_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("La quantité ne peut pas être négative.")
        return value


class TaskListSerializer(serializers.ModelSerializer):
    task_progress     = serializers.ReadOnlyField()
    weighted_progress = serializers.ReadOnlyField()

    class Meta:
        model  = Task
        fields = [
            'id', 'order', 'name', 'sub_activity', 'unit',
            'total_quantity', 'realized_quantity', 'weight',
            'task_progress', 'weighted_progress',
            'planned_start', 'planned_end',
        ]


class WeeklyTaskDetailSerializer(serializers.ModelSerializer):
    task_gap = serializers.ReadOnlyField()

    class Meta:
        model  = WeeklyTaskDetail
        fields = [
            'id', 'task', 'quantity_this_week', 'cumulative_quantity',
            'task_progress_snapshot', 'planned_progress', 'task_gap',
            'problem', 'corrective_action',
            'action_responsible', 'resolution_deadline',
        ]


class WeeklyReportSerializer(serializers.ModelSerializer):
    task_details    = WeeklyTaskDetailSerializer(many=True, required=False)
    progress_gap    = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model  = WeeklyReport
        fields = [
            'id', 'project', 'week_number', 'year', 'report_date',
            'global_progress_snapshot', 'planned_progress', 'progress_gap',
            'delay_gap_days',
            'weather', 'summary', 'problems', 'corrective_actions',
            'decision_expected', 'next_week_plan', 'task_details',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        task_details_data = validated_data.pop('task_details', [])
        report = WeeklyReport.objects.create(**validated_data)
        for detail_data in task_details_data:
            task_obj = detail_data.get('task')
            task_id  = task_obj.id if hasattr(task_obj, 'id') else int(task_obj)
            WeeklyTaskDetail.objects.create(
                weekly_report=report,
                task_id=task_id,
                quantity_this_week=detail_data.get('quantity_this_week', 0),
                cumulative_quantity=detail_data.get('cumulative_quantity', 0),
                task_progress_snapshot=detail_data.get('task_progress_snapshot', 0),
                planned_progress=detail_data.get('planned_progress', 0),
                problem=detail_data.get('problem', ''),
                corrective_action=detail_data.get('corrective_action', ''),
                resolution_deadline=detail_data.get('resolution_deadline', None),
            )
            try:
                task = Task.objects.get(pk=task_id)
                task.realized_quantity = detail_data.get('cumulative_quantity', task.realized_quantity)
                task.save(update_fields=['realized_quantity', 'updated_at'])
            except Task.DoesNotExist:
                pass
        return report


class WeeklyReportListSerializer(serializers.ModelSerializer):
    progress_gap    = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model  = WeeklyReport
        fields = [
            'id', 'week_number', 'year', 'report_date',
            'global_progress_snapshot', 'planned_progress', 'progress_gap',
            'delay_gap_days', 'weather', 'summary', 'decision_expected',
            'created_by_name', 'created_at',
        ]


class ProjectSerializer(serializers.ModelSerializer):
    global_progress      = serializers.ReadOnlyField()
    total_weight         = serializers.ReadOnlyField()
    is_on_schedule       = serializers.ReadOnlyField()
    project_manager_name = serializers.SerializerMethodField()
    validated_by_name    = serializers.CharField(source='validated_by.username', read_only=True)
    task_count           = serializers.SerializerMethodField()
    last_report_date     = serializers.SerializerMethodField()

    # ── Budget ────────────────────────────────────────────────────────────────
    budget_consomme    = serializers.ReadOnlyField()
    budget_restant     = serializers.ReadOnlyField()
    budget_depasse     = serializers.ReadOnlyField()
    budget_pourcentage = serializers.ReadOnlyField()

    # ── Blocage automatique du budget (Évolution 6) ─────────────────────────
    budget_unblocked_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'code', 'name', 'description', 'client', 'location',
            'contract_date', 'start_date', 'planned_end_date', 'actual_end_date',
            'project_manager', 'project_manager_name',
            'status', 'validated_by_dg', 'validated_by_name', 'validated_at',
            'planning_validated', 'planning_validated_at',
            # Budget
            'budget', 'budget_consomme', 'budget_restant',
            'budget_depasse', 'budget_pourcentage',
            'is_budget_blocked', 'budget_blocked_at', 'budget_block_reason',
            'budget_unblocked_by_name', 'budget_unblocked_at',
            # Avancement
            'global_progress', 'total_weight', 'is_on_schedule',
            'task_count', 'last_report_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'validated_by_dg', 'validated_by', 'validated_at',
            'planning_validated', 'planning_validated_at',
            'is_budget_blocked', 'budget_blocked_at', 'budget_block_reason',
            'budget_unblocked_by', 'budget_unblocked_at',
            'created_at', 'updated_at',
        ]

    def get_budget_unblocked_by_name(self, obj):
        if obj.budget_unblocked_by:
            return obj.budget_unblocked_by.get_full_name() or obj.budget_unblocked_by.username
        return None

    def get_project_manager_name(self, obj):
        if obj.project_manager:
            return obj.project_manager.get_full_name() or obj.project_manager.username
        return None

    def get_task_count(self, obj):
        return obj.tasks.filter(is_active=True).count()

    def get_last_report_date(self, obj):
        last = obj.weekly_reports.order_by('-report_date').first()
        return last.report_date if last else None