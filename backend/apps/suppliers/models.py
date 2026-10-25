from django.db import models


class Supplier(models.Model):
    name           = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=100, blank=True)
    phone          = models.CharField(max_length=30, blank=True)
    email          = models.EmailField(blank=True)
    address        = models.TextField(blank=True)
    city           = models.CharField(max_length=100, blank=True)
    notes          = models.TextField(blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_orders(self):
        return self.requests.filter(request_type='achat').count()

    @property
    def validated_orders(self):
        return self.requests.filter(
            request_type='achat', status__in=['validee', 'executee']
        ).count()

    # ── Indicateur de performance fournisseur (Phase F — traçabilité achats) ──
    @property
    def _commandes_livrees(self):
        """Commandes achat réceptionnées avec une date prévue ET réelle
        renseignées. Les codes d'étape ne sont jamais figés en dur : le RAL
        peut renommer/reconfigurer le circuit logistique (voir
        LogisticsStageViewSet) — on résout donc dynamiquement les étapes
        marquées réception/clôture pour ce type de demande, comme le fait
        déjà UnifiedRequest._logistics_reception_stage/_logistics_closed_stage."""
        from apps.requests.models import LogisticsStage
        from django.db.models import Q
        stage_codes = list(
            LogisticsStage.objects.filter(
                Q(is_reception_stage=True) | Q(is_closing_stage=True),
                request_type='achat', is_active=True,
            ).values_list('code', flat=True)
        )
        if not stage_codes:
            return self.requests.none()
        return self.requests.filter(
            request_type='achat',
            logistics_status__in=stage_codes,
            date_livraison_prevue__isnull=False,
            date_livraison_reelle__isnull=False,
        )

    @property
    def taux_livraison_a_temps(self):
        """Pourcentage de commandes livrées à la date prévue ou avant."""
        qs    = self._commandes_livrees
        total = qs.count()
        if total == 0:
            return None
        from django.db.models import F
        a_temps = qs.filter(date_livraison_reelle__lte=F('date_livraison_prevue')).count()
        return round((a_temps / total) * 100, 1)

    @property
    def delai_moyen_jours(self):
        """Écart moyen (en jours) entre date prévue et date réelle — positif = retard moyen."""
        qs = self._commandes_livrees
        if not qs.exists():
            return None
        ecarts = [(r.date_livraison_reelle - r.date_livraison_prevue).days for r in qs]
        return round(sum(ecarts) / len(ecarts), 1)

    @property
    def commandes_en_retard_count(self):
        return sum(1 for r in self.requests.filter(request_type='achat') if r.est_en_retard)