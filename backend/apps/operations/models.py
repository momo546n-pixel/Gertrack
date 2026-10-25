from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User
from gertrack.business_rules import PROJECT_BUDGET_BLOCK_THRESHOLD_PERCENT


# ─────────────────────────────────────────────────────────────────────────────
# PROJET
# ─────────────────────────────────────────────────────────────────────────────

class Project(models.Model):

    STATUS_DRAFT      = 'brouillon'
    STATUS_ACTIVE     = 'en_cours'
    STATUS_ON_HOLD    = 'suspendu'
    STATUS_COMPLETED  = 'termine'
    STATUS_CANCELLED  = 'annule'

    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Brouillon'),
        (STATUS_ACTIVE,    'En cours'),
        (STATUS_ON_HOLD,   'Suspendu'),
        (STATUS_COMPLETED, 'Terminé'),
        (STATUS_CANCELLED, 'Annulé'),
    ]

    code             = models.CharField(max_length=30, unique=True)
    name             = models.CharField(max_length=255)
    description      = models.TextField(blank=True)
    client           = models.CharField(max_length=255, blank=True)
    location         = models.CharField(max_length=255, blank=True)

    contract_date    = models.DateField(null=True, blank=True)
    start_date       = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_end_date  = models.DateField(null=True, blank=True)

    project_manager  = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_projects',
        verbose_name='Chef de projet'
    )

    status           = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    validated_by_dg  = models.BooleanField(default=False)
    validated_by     = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='validated_projects'
    )
    validated_at     = models.DateTimeField(null=True, blank=True)

    planning_validated    = models.BooleanField(default=False)
    planning_validated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='validated_plannings'
    )
    planning_validated_at = models.DateTimeField(null=True, blank=True)

    budget           = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    # ── Blocage automatique du budget (Évolution 6) ─────────────────────────
    # Figé volontairement : une fois déclenché, `is_budget_blocked` ne
    # redevient jamais False tout seul (même si la consommation ou
    # l'avancement s'améliorent ensuite) — seul un déblocage manuel du DG
    # (voir Project.unblock_budget) peut le lever. Voir
    # Project.check_and_apply_budget_block pour la condition de déclenchement.
    is_budget_blocked   = models.BooleanField(default=False, verbose_name='Budget bloqué')
    budget_blocked_at   = models.DateTimeField(null=True, blank=True)
    budget_block_reason = models.TextField(blank=True)
    budget_unblocked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projects_budget_unblocked'
    )
    budget_unblocked_at = models.DateTimeField(null=True, blank=True)

    created_by       = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='created_projects'
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Projet'
        verbose_name_plural = 'Projets'

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def global_progress(self):
        tasks = self.tasks.filter(is_active=True)
        if not tasks.exists():
            return 0.0
        total_contribution = sum(task.weighted_progress for task in tasks)
        return round(total_contribution, 2)

    @property
    def total_weight(self):
        return sum(t.weight for t in self.tasks.filter(is_active=True))

    @property
    def is_on_schedule(self):
        from django.utils import timezone
        if not self.planned_end_date:
            return None
        return timezone.now().date() <= self.planned_end_date

    # ── Budget (NOUVEAU) ──────────────────────────────────────────────────────

    @property
    def budget_consomme(self):
        """Somme des demandes d'achat réellement EXÉCUTÉES liées à ce projet
        (Évolution 7) — une simple validation ne consomme jamais le budget,
        exactement la même règle que RALBudget.montant_consomme. Pour un
        achat, `status` ne passe à 'executee' qu'à l'exécution par le
        Responsable Financier (voir UnifiedRequest.execute_financial),
        jamais à la validation ni à la réception magasin."""
        try:
            from apps.requests.models import UnifiedRequest
            requests_qs = UnifiedRequest.objects.filter(
                project=self,
                status='executee',
                request_type='achat',
            ).prefetch_related('items')
            total = 0
            for req in requests_qs:
                for item in req.items.all():
                    if item.unit_price is not None:
                        total += float(item.quantity) * float(item.unit_price)
            return round(total, 2)
        except Exception:
            return 0.0

    @property
    def budget_restant(self):
        if self.budget is None:
            return None
        return round(float(self.budget) - self.budget_consomme, 2)

    @property
    def budget_depasse(self):
        if self.budget is None:
            return False
        return self.budget_consomme > float(self.budget)

    @property
    def budget_pourcentage(self):
        if not self.budget or float(self.budget) == 0:
            return 0
        return round((self.budget_consomme / float(self.budget)) * 100, 1)

    # ── Blocage automatique du budget (Évolution 6) ─────────────────────────
    @property
    def latest_weekly_report(self):
        return self.weekly_reports.order_by('-year', '-week_number').first()

    @property
    def is_progress_below_expected(self):
        """L'écart avancement réel / attendu du dernier rapport hebdomadaire
        (WeeklyReport.progress_gap, déjà calculé pour le suivi hebdomadaire)
        fait référence — pas de nouvelle règle métier. Sans rapport, l'écart
        est indéterminé : on ne bloque jamais sur une inconnue (évite un
        faux positif sur un projet qui n'a simplement pas encore de suivi)."""
        report = self.latest_weekly_report
        if report is None:
            return False
        return report.progress_gap < 0

    @property
    def should_auto_block_budget(self):
        """Condition live des deux critères (Évolution 6) — évaluée à
        chaque déclencheur potentiel (validation d'un achat lié, nouveau
        rapport hebdomadaire), jamais recalculée après coup une fois le
        blocage posé (voir is_budget_blocked, figé jusqu'au déblocage
        manuel)."""
        return (
            self.budget_pourcentage >= PROJECT_BUDGET_BLOCK_THRESHOLD_PERCENT
            and self.is_progress_below_expected
        )

    def check_and_apply_budget_block(self):
        """Applique le blocage si la condition est réunie et qu'il n'est pas
        déjà posé. Ne fait jamais rien si déjà bloqué (figé jusqu'au
        déblocage manuel) — retourne True seulement si le blocage vient
        d'être posé par CET appel (pour ne notifier le DG qu'une fois)."""
        if self.is_budget_blocked:
            return False
        if not self.should_auto_block_budget:
            return False
        from django.utils import timezone
        report = self.latest_weekly_report
        self.is_budget_blocked = True
        self.budget_blocked_at = timezone.now()
        self.budget_block_reason = (
            f"Budget consommé à {self.budget_pourcentage}% (seuil "
            f"{PROJECT_BUDGET_BLOCK_THRESHOLD_PERCENT}%) et avancement en retard "
            f"(écart {report.progress_gap}% au dernier rapport S{report.week_number}/{report.year})."
        )
        self.save(update_fields=['is_budget_blocked', 'budget_blocked_at', 'budget_block_reason', 'updated_at'])
        return True

    def unblock_budget(self, user):
        from django.utils import timezone
        self.is_budget_blocked   = False
        self.budget_unblocked_by = user
        self.budget_unblocked_at = timezone.now()
        self.save(update_fields=['is_budget_blocked', 'budget_unblocked_by', 'budget_unblocked_at', 'updated_at'])


# ─────────────────────────────────────────────────────────────────────────────
# TÂCHE / ACTIVITÉ
# ─────────────────────────────────────────────────────────────────────────────

class Task(models.Model):

    project            = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tasks'
    )
    order              = models.PositiveIntegerField(default=0)
    name               = models.CharField(max_length=255)
    description        = models.TextField(blank=True)
    unit               = models.CharField(max_length=50, blank=True)
    sub_activity       = models.CharField(max_length=255, blank=True)
    comment            = models.TextField(blank=True)

    total_quantity     = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    realized_quantity  = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    weight             = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    planned_start      = models.DateField(null=True, blank=True)
    planned_end        = models.DateField(null=True, blank=True)

    responsible        = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_tasks'
    )

    is_active          = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['order', 'id']
        verbose_name        = 'Tâche'
        verbose_name_plural = 'Tâches'

    def __str__(self):
        return f"{self.project.code} — {self.name}"

    @property
    def task_progress(self):
        if not self.total_quantity or self.total_quantity == 0:
            return 0.0
        progress = (float(self.realized_quantity) / float(self.total_quantity)) * 100
        return round(min(progress, 100.0), 2)

    @property
    def weighted_progress(self):
        return round((self.task_progress * float(self.weight)) / 100, 4)

    @property
    def remaining_quantity(self):
        return max(float(self.total_quantity) - float(self.realized_quantity), 0)


# ─────────────────────────────────────────────────────────────────────────────
# SUIVI HEBDOMADAIRE
# ─────────────────────────────────────────────────────────────────────────────

class WeeklyReport(models.Model):

    project                  = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='weekly_reports'
    )
    week_number              = models.PositiveIntegerField()
    year                     = models.PositiveIntegerField()
    report_date              = models.DateField()
    global_progress_snapshot = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    planned_progress         = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def progress_gap(self):
        return round(float(self.global_progress_snapshot) - float(self.planned_progress), 2)

    WEATHER_OK       = 'ok'
    WEATHER_RISK     = 'risque'
    WEATHER_CRITICAL = 'critique'
    WEATHER_CHOICES  = [
        (WEATHER_OK,       'OK — Dans les délais'),
        (WEATHER_RISK,     'Risque — Vigilance requise'),
        (WEATHER_CRITICAL, 'Critique — Action urgente'),
    ]
    weather                  = models.CharField(max_length=10, choices=WEATHER_CHOICES, default=WEATHER_OK)
    delay_gap_days           = models.IntegerField(default=0)
    decision_expected        = models.TextField(blank=True)
    summary                  = models.TextField(blank=True)
    problems                 = models.TextField(blank=True)
    corrective_actions       = models.TextField(blank=True)
    next_week_plan           = models.TextField(blank=True)

    created_by               = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='created_reports'
    )
    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        ordering        = ['-year', '-week_number']
        unique_together = [['project', 'week_number', 'year']]
        verbose_name        = 'Rapport hebdomadaire'
        verbose_name_plural = 'Rapports hebdomadaires'

    def __str__(self):
        return f"{self.project.code} — S{self.week_number}/{self.year}"


# ─────────────────────────────────────────────────────────────────────────────
# DÉTAIL TÂCHE PAR SEMAINE
# ─────────────────────────────────────────────────────────────────────────────

class WeeklyTaskDetail(models.Model):

    weekly_report           = models.ForeignKey(
        WeeklyReport, on_delete=models.CASCADE, related_name='task_details'
    )
    task                    = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name='weekly_details'
    )
    quantity_this_week      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cumulative_quantity     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    task_progress_snapshot  = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    planned_progress        = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def task_gap(self):
        return round(float(self.task_progress_snapshot) - float(self.planned_progress), 2)

    problem               = models.TextField(blank=True)
    corrective_action     = models.TextField(blank=True)
    action_responsible    = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='action_tasks'
    )
    resolution_deadline   = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [['weekly_report', 'task']]
        ordering        = ['task__order']
        verbose_name    = 'Détail tâche hebdomadaire'

    def __str__(self):
        return f"{self.weekly_report} — {self.task.name}"