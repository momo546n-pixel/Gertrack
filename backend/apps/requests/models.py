from django.db import models, transaction, IntegrityError
from django.utils import timezone
from apps.accounts.models import User
from gertrack.business_rules import (
    RAL_BUDGET_BLOCK_THRESHOLD_PERCENT,
    RAL_BUDGET_REQUEST_TYPE,
    ROLE_RAL,
    REQUEST_FINAL_STATUSES,
    REQUEST_STATUSES_ELIGIBLE_FOR_LOGISTICS,
    REQUEST_STATUS_EXECUTED,
    VALIDATION_TYPE_URGENT,
    REQUEST_STATUS_AWAITING_DOP_OR_DG,
)


class DuplicateExecutionError(ValueError):
    """Levée quand une action d'exécution (validation DG, avancement du
    circuit logistique) est retentée sur une demande déjà exécutée ou déjà
    à cette étape — double-clic, retry réseau, appel concurrent. Sous-classe
    de ValueError (donc toujours interceptée par un `except ValueError`
    existant) mais distincte pour permettre à la vue de journaliser
    spécifiquement ces tentatives dans l'AuditLog (voir views.py)."""
    pass


class UnifiedRequest(models.Model):

    REQUEST_TYPE_CHOICES = [
        ('achat',      'Demande Achat'),
        ('entree',     'Entrée Stock'),
        ('sortie',     'Sortie Stock'),
        ('ajustement', 'Ajustement Stock'),
    ]

    VALIDATION_TYPE_CHOICES = [
        ('dg_only',              'DG uniquement'),
        ('dop_then_dg',          'DOP puis DG'),
        (VALIDATION_TYPE_URGENT, 'Urgent — DOP ou DG (le premier valide)'),
    ]

    STATUS_CHOICES = [
        ('brouillon',      'Brouillon'),
        ('en_attente_dop', 'En attente DOP'),
        ('en_attente_dg',  'En attente DG'),
        (REQUEST_STATUS_AWAITING_DOP_OR_DG, 'En attente DOP ou DG (urgent)'),
        ('validee',        'Validée'),
        ('refusee',        'Refusée'),
        ('executee',       'Exécutée'),
    ]

    reference       = models.CharField(max_length=30, unique=True, blank=True)
    request_type    = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    validation_type = models.CharField(max_length=20, choices=VALIDATION_TYPE_CHOICES, default='dg_only')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='brouillon')

    # Distinct de `status` ci-dessus (circuit de validation DOP/DG/RAL) : une
    # fois la demande "validee", le suivi logistique avance dans ce circuit
    # séparé, sans jamais modifier le sens de `status`. Les étapes possibles
    # ne sont plus figées en dur ici — voir LogisticsStage, configurable par
    # le Responsable Achat et Logistique (RAL).
    logistics_status       = models.CharField(max_length=30, blank=True)
    date_livraison_prevue  = models.DateField(null=True, blank=True, verbose_name='Date de livraison prévue')
    date_livraison_reelle  = models.DateField(null=True, blank=True, verbose_name='Date de livraison réelle')

    # Réception chantier (sortie) — doit être confirmée par le Chef de Projet
    reception_confirmed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='confirmed_receptions',
    )
    reception_confirmed_at = models.DateTimeField(null=True, blank=True)

    # Exécution financière (Évolution 7) — achat uniquement. Distincte de la
    # réception magasin (reception_confirmed_by/at ci-dessus concerne les
    # sorties chantier) : c'est ici que le Responsable Financier exécute la
    # commande, AVANT le circuit logistique — jamais à la réception, qui
    # reste un événement séparé ne déclenchant que les mouvements de stock
    # (voir UnifiedRequest.execute_financial / _execute_stock_movements).
    financial_execution_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='financial_executions',
    )
    financial_execution_at    = models.DateTimeField(null=True, blank=True)
    financial_execution_notes = models.TextField(blank=True)

    warehouse = models.ForeignKey(
        'stock.Warehouse',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='requests',
        verbose_name='Magasin'
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='requests',
        verbose_name='Fournisseur'
    )
    project = models.ForeignKey(
        'operations.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='requests',
        verbose_name='Projet'
    )

    # Demande d'achat urgente (Évolution 5) — réservée à un sous-ensemble de
    # rôles et obligatoirement liée à un projet (voir UnifiedRequestViewSet.
    # _enforce_role_constraints/_forced_validation_type, seuls points
    # d'écriture réels : le rôle et le circuit de validation sont forcés
    # côté serveur, jamais choisis librement par le client).
    is_urgent = models.BooleanField(default=False, verbose_name='Urgente')

    # Budget annuel RAL dont cette demande d'achat est déduite — obligatoire
    # pour toute demande d'achat (Évolution 4 : voir
    # UnifiedRequestViewSet.perform_create/perform_update, seuls points
    # d'écriture de ce champ, jamais modifiable directement par le client —
    # voir read_only_fields dans les serializers). `on_delete=PROTECT` :
    # le DG ne peut pas supprimer un budget déjà utilisé par des demandes.
    # `null=True` car seules les demandes d'achat sont concernées ; les
    # autres types (entrée/sortie/ajustement) n'ont pas de budget.
    budget = models.ForeignKey(
        'RALBudget',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='requests',
        verbose_name='Budget annuel RAL'
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='unified_requests',
        verbose_name='Demandeur'
    )

    motif       = models.TextField(blank=True, verbose_name='Motif')
    notes       = models.TextField(blank=True)
    date_needed = models.DateField(null=True, blank=True, verbose_name='Date souhaitée')
    proforma    = models.FileField(upload_to='proformas/%Y/%m/', null=True, blank=True)

    # Validation DOP
    dop_validated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dop_validations'
    )
    dop_validated_at = models.DateTimeField(null=True, blank=True)
    dop_comment      = models.TextField(blank=True)

    # Validation DG
    dg_validated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dg_validations'
    )
    dg_validated_at = models.DateTimeField(null=True, blank=True)
    dg_comment      = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Demande'
        verbose_name_plural = 'Demandes'

    def __str__(self):
        return f"{self.reference} — {self.get_request_type_display()}"

    # ── Génération référence automatique ─────────────────────────────────────
    # count()+1 n'est pas fiable : un écart (suppression, données de seed non
    # séquentielles) fait recalculer un numéro déjà pris et casse la contrainte
    # unique. On repart du plus grand suffixe existant, sous verrou (select_for_
    # update) pour sérialiser les créations concurrentes, avec une nouvelle
    # tentative si une collision survient malgré tout (ex. tout premier numéro
    # de l'année, où aucune ligne n'existe encore à verrouiller).
    REFERENCE_PREFIXES = {
        'achat':      'DA',
        'entree':     'ES',
        'sortie':     'BS',
        'ajustement': 'AJ',
    }

    def save(self, *args, **kwargs):
        if self.reference:
            super().save(*args, **kwargs)
            return
        last_error = None
        for _ in range(5):
            try:
                with transaction.atomic():
                    self.reference = self._generate_reference()
                    super().save(*args, **kwargs)
                return
            except IntegrityError as e:
                last_error = e
                self.reference = ''
        raise last_error

    def _generate_reference(self):
        year    = timezone.now().year
        prefix  = self.REFERENCE_PREFIXES.get(self.request_type, 'DR')
        pattern = f"{prefix}-{year}-"
        existing_refs = UnifiedRequest.objects.select_for_update().filter(
            request_type=self.request_type,
            reference__startswith=pattern,
        ).values_list('reference', flat=True)
        last_num = 0
        for ref in existing_refs:
            try:
                last_num = max(last_num, int(ref.rsplit('-', 1)[-1]))
            except ValueError:
                continue
        return f"{pattern}{last_num + 1:04d}"

    # ── Propriété montant total ───────────────────────────────────────────────
    @property
    def total_amount(self):
        total = 0
        for item in self.items.all():
            if item.unit_price is not None:
                total += item.quantity * item.unit_price
        return total

    # ── Workflow ──────────────────────────────────────────────────────────────
    def submit(self):
        if self.status != 'brouillon':
            raise ValueError("Seul un brouillon peut être soumis.")
        if self.validation_type == VALIDATION_TYPE_URGENT:
            self.status = REQUEST_STATUS_AWAITING_DOP_OR_DG
        elif self.validation_type == 'dop_then_dg':
            self.status = 'en_attente_dop'
        else:
            self.status = 'en_attente_dg'
        self.save(update_fields=['status', 'updated_at'])

    # ── Course DOP/DG pour les demandes urgentes (Évolution 5) ────────────────
    # Le premier acte (validation OU refus) décide seul du sort de la demande
    # — l'action de l'autre devient caduque. Réutilise le même verrou de ligne
    # que validate_dg/advance_logistics pour empêcher que deux appels quasi
    # simultanés (le vrai scénario de course, pas seulement un double-clic)
    # traitent tous les deux la demande.
    def _act_on_urgent(self, user, comment, outcome, actor):
        with transaction.atomic():
            locked = UnifiedRequest.objects.select_for_update().get(pk=self.pk)
            self.__dict__.update(locked.__dict__)

            if self.status != REQUEST_STATUS_AWAITING_DOP_OR_DG:
                autre = 'DG' if actor == 'dop' else 'DOP'
                raise DuplicateExecutionError(
                    f"Cette demande urgente a déjà été traitée par le {autre} "
                    f"(statut actuel : « {self.get_status_display()} ») — cette action arrive trop tard."
                )

            now = timezone.now()
            if actor == 'dop':
                self.dop_validated_by = user
                self.dop_validated_at = now
                self.dop_comment      = comment
            else:
                self.dg_validated_by = user
                self.dg_validated_at = now
                self.dg_comment      = comment

            self.status = outcome
            self.save()
            if outcome == 'validee' and self.request_type in ('entree', 'sortie', 'ajustement'):
                self._execute_stock_movements()

    def validate_dop(self, user, comment=''):
        if self.validation_type == VALIDATION_TYPE_URGENT:
            return self._act_on_urgent(user, comment, 'validee', 'dop')
        if self.status != 'en_attente_dop':
            raise ValueError("La demande n'est pas en attente DOP.")
        self.dop_validated_by = user
        self.dop_validated_at = timezone.now()
        self.dop_comment      = comment
        self.status           = 'en_attente_dg'
        self.save()

    def reject_dop(self, user, comment=''):
        if self.validation_type == VALIDATION_TYPE_URGENT:
            return self._act_on_urgent(user, comment, 'refusee', 'dop')
        if self.status != 'en_attente_dop':
            raise ValueError("La demande n'est pas en attente DOP.")
        self.dop_validated_by = user
        self.dop_validated_at = timezone.now()
        self.dop_comment      = comment
        self.status           = 'refusee'
        self.save()

    def validate_dg(self, user, comment=''):
        if self.validation_type == VALIDATION_TYPE_URGENT:
            return self._act_on_urgent(user, comment, 'validee', 'dg')
        # Verrou de ligne : sans lui, deux appels concurrents (double-clic,
        # nouvelle tentative réseau, requêtes simultanées) pourraient tous
        # les deux lire "en_attente_dg" avant que l'un des deux ait
        # sauvegardé, et créer deux fois les mouvements de stock associés.
        with transaction.atomic():
            locked = UnifiedRequest.objects.select_for_update().get(pk=self.pk)
            self.__dict__.update(locked.__dict__)

            if self.status in REQUEST_FINAL_STATUSES:
                raise DuplicateExecutionError(
                    f"Cette demande a déjà été traitée (statut actuel : "
                    f"« {self.get_status_display()} ») — elle ne peut pas être validée une seconde fois."
                )
            if self.status != 'en_attente_dg':
                raise ValueError("La demande n'est pas en attente DG.")
            self.dg_validated_by = user
            self.dg_validated_at = timezone.now()
            self.dg_comment      = comment
            self.status          = 'validee'
            self.save()
            if self.request_type in ('entree', 'sortie', 'ajustement'):
                self._execute_stock_movements()

    def reject_dg(self, user, comment=''):
        if self.validation_type == VALIDATION_TYPE_URGENT:
            return self._act_on_urgent(user, comment, 'refusee', 'dg')
        if self.status != 'en_attente_dg':
            raise ValueError("La demande n'est pas en attente DG.")
        self.dg_validated_by = user
        self.dg_validated_at = timezone.now()
        self.dg_comment      = comment
        self.status          = 'refusee'
        self.save()

    # ── Exécution financière (Évolution 7) ─────────────────────────────────
    # Réservée aux demandes d'achat validées. C'est ici — et seulement ici —
    # que `status` passe à 'executee' pour un achat désormais : plus à la
    # réception magasin (voir advance_logistics/_execute_stock_movements,
    # qui restent inchangés et continuent de gérer exclusivement la
    # réception physique et les mouvements de stock). Même garde
    # anti-double-exécution que validate_dg/advance_logistics : verrou de
    # ligne + DuplicateExecutionError si déjà exécutée (double-clic, retry,
    # appel concurrent).
    def execute_financial(self, user, notes=''):
        with transaction.atomic():
            locked = UnifiedRequest.objects.select_for_update().get(pk=self.pk)
            self.__dict__.update(locked.__dict__)

            if self.request_type != RAL_BUDGET_REQUEST_TYPE:
                raise ValueError("Seule une demande d'achat peut être exécutée par le Responsable Financier.")
            if self.status == REQUEST_STATUS_EXECUTED:
                when = f" le {self.financial_execution_at:%d/%m/%Y à %H:%M}" if self.financial_execution_at else ""
                raise DuplicateExecutionError(
                    f"Cette demande a déjà été exécutée{when} — elle ne peut pas l'être une seconde fois."
                )
            if self.status != 'validee':
                raise ValueError(
                    f"La demande doit être validée avant de pouvoir être exécutée "
                    f"(statut actuel : « {self.get_status_display()} »)."
                )

            self.financial_execution_by    = user
            self.financial_execution_at    = timezone.now()
            self.financial_execution_notes = notes
            self.status                    = 'executee'
            self.save()

    def _execute_stock_movements(self):
        """Crée les mouvements de stock automatiquement (validation DG pour
        entrée/sortie/ajustement, ou réception magasin pour un achat)."""
        from apps.stock.models import StockMovement

        type_map = {
            'entree':     StockMovement.ENTRY,
            'sortie':     StockMovement.EXIT,
            'ajustement': StockMovement.ADJUSTMENT,
            'achat':      StockMovement.ENTRY,
        }
        movement_type = type_map.get(self.request_type)
        origin        = 'achat' if self.request_type == 'achat' else 'manuel'

        for item in self.items.all():
            try:
                StockMovement.objects.create(
                    product       = item.product,
                    movement_type = movement_type,
                    quantity      = item.quantity,
                    date          = timezone.now().date(),
                    warehouse     = self.warehouse,
                    origin        = origin,
                    origin_ref    = self.reference,
                    notes         = f"Exécution automatique — {self.reference}",
                    created_by    = self.dg_validated_by,
                )
            except ValueError as e:
                raise ValueError(f"Erreur mouvement {item.product.code} : {e}")

        self.status = 'executee'
        self.save(update_fields=['status', 'updated_at'])

    # ── Circuit logistique (configurable — voir LogisticsStage) ───────────────
    @property
    def _logistics_order(self):
        """Codes des étapes actives du circuit logistique de ce type de
        demande, dans l'ordre configuré par le Responsable Achat et
        Logistique (RAL). None si aucun circuit n'est défini pour ce type."""
        codes = list(
            LogisticsStage.objects
            .filter(request_type=self.request_type, is_active=True)
            .order_by('order', 'id')
            .values_list('code', flat=True)
        )
        return codes or None

    @property
    def _logistics_reception_stage(self):
        """Étape de réception du circuit (marquée par le RAL) : réception
        magasin pour un achat, chantier pour une sortie, ou toute autre
        étape que le RAL aura désignée pour un futur type de demande."""
        stage = LogisticsStage.objects.filter(
            request_type=self.request_type, is_active=True, is_reception_stage=True
        ).first()
        return stage.code if stage else None

    @property
    def _logistics_closed_stage(self):
        stage = LogisticsStage.objects.filter(
            request_type=self.request_type, is_active=True, is_closing_stage=True
        ).first()
        return stage.code if stage else None

    @property
    def logistics_status_label(self):
        """Libellé de l'étape logistique courante, tel que défini par le RAL."""
        if not self.logistics_status:
            return ''
        stage = LogisticsStage.objects.filter(
            request_type=self.request_type, code=self.logistics_status
        ).first()
        return stage.label if stage else self.logistics_status

    @property
    def est_en_retard(self):
        """Retard automatique : dépassement de la date prévue sans réception effective."""
        if not self._logistics_order or not self.date_livraison_prevue:
            return False
        if self.date_livraison_reelle:
            return self.date_livraison_reelle > self.date_livraison_prevue
        if self.logistics_status in (self._logistics_reception_stage, self._logistics_closed_stage):
            return False
        return timezone.now().date() > self.date_livraison_prevue

    def advance_logistics(self, new_status, user, date_livraison_prevue=None):
        """
        Fait avancer le circuit logistique (achat ou sortie) à l'étape
        suivante. Les contrôles de permission (qui a le droit d'appeler ceci,
        et l'exigence que la « réception chantier » d'une sortie soit
        confirmée par le Chef de Projet du projet concerné) sont du ressort
        de la vue, comme pour le reste du circuit de validation DOP/DG.

        Toute la vérification + mise à jour se fait sous verrou de ligne
        (select_for_update) : sans lui, deux appels concurrents (double-clic,
        nouvelle tentative réseau, requêtes simultanées) pourraient tous les
        deux lire "pas encore à cette étape" avant que l'un des deux ait
        sauvegardé, et exécuter deux fois les effets de bord — notamment le
        mouvement de stock d'un achat à la réception, qui ne doit jamais être
        créé deux fois pour la même demande (double consommation du budget
        RAL une fois le Responsable Financier branché dessus).
        """
        with transaction.atomic():
            locked = UnifiedRequest.objects.select_for_update().get(pk=self.pk)
            self.__dict__.update(locked.__dict__)

            order = self._logistics_order
            if order is None:
                raise ValueError("Aucun circuit logistique n'est configuré pour ce type de demande.")
            if self.status not in REQUEST_STATUSES_ELIGIBLE_FOR_LOGISTICS:
                # Pour un achat (Évolution 7), la validation seule ne suffit
                # plus : le Responsable Financier doit d'abord exécuter la
                # commande (voir execute_financial) avant que le circuit
                # logistique puisse démarrer.
                raise ValueError(
                    "La demande doit être exécutée avant d'entrer dans le circuit logistique."
                    if self.request_type == RAL_BUDGET_REQUEST_TYPE else
                    "La demande doit être validée avant d'entrer dans le circuit logistique."
                )
            if new_status not in order:
                raise ValueError("Statut logistique invalide pour ce type de demande.")

            if date_livraison_prevue and isinstance(date_livraison_prevue, str):
                from django.utils.dateparse import parse_date
                parsed = parse_date(date_livraison_prevue)
                if parsed is None:
                    raise ValueError("Format de date de livraison prévue invalide (attendu : AAAA-MM-JJ).")
                date_livraison_prevue = parsed

            current_index = order.index(self.logistics_status) if self.logistics_status in order else -1
            new_index     = order.index(new_status)
            # `<=` (et pas seulement `<`) : une demande déjà à cette étape
            # (double-clic, retry) ne doit jamais réexécuter les effets de
            # bord une seconde fois — pas seulement le retour en arrière.
            if self.logistics_status and new_index <= current_index:
                raise DuplicateExecutionError(
                    f"Cette étape a déjà été atteinte — la demande est déjà au statut "
                    f"« {self.logistics_status_label} » et ne peut pas être exécutée deux fois."
                )

            reception_stage = self._logistics_reception_stage

            # Calculé AVANT de faire avancer le statut : `est_en_retard` ignore les
            # demandes déjà réceptionnées, donc il faut évaluer le retard pendant
            # que la demande est encore "en attente" de livraison.
            was_late = False
            if new_status == reception_stage and self.date_livraison_prevue:
                was_late = timezone.now().date() > self.date_livraison_prevue

            self.logistics_status = new_status
            if date_livraison_prevue:
                self.date_livraison_prevue = date_livraison_prevue
            self.save(update_fields=['logistics_status', 'date_livraison_prevue', 'updated_at'])

            if new_status == reception_stage:
                self.date_livraison_reelle = timezone.now().date()
                update_fields = ['date_livraison_reelle', 'updated_at']
                if self.request_type == 'sortie':
                    # La réception chantier d'une sortie doit être confirmée par
                    # le Chef de Projet — tracé séparément du circuit DOP/DG.
                    self.reception_confirmed_by = user
                    self.reception_confirmed_at = timezone.now()
                    update_fields += ['reception_confirmed_by', 'reception_confirmed_at']
                self.save(update_fields=update_fields)

                # Le mouvement de stock d'une sortie a déjà été créé à la
                # validation DG (comportement existant, inchangé) ; pour un achat
                # en revanche, le stock n'augmente qu'à la réception magasin.
                if self.request_type == 'achat':
                    self._execute_stock_movements()

            return was_late


class RequestItem(models.Model):
    request    = models.ForeignKey(
        UnifiedRequest, on_delete=models.CASCADE, related_name='items'
    )
    product    = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE
    )
    quantity   = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes      = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name        = 'Article demande'
        verbose_name_plural = 'Articles demande'

    def __str__(self):
        return f"{self.product.code} × {self.quantity}"

    @property
    def total_price(self):
        if self.unit_price is not None:
            return float(self.quantity) * float(self.unit_price)
        return None


class LogisticsStage(models.Model):
    """
    Étape du circuit logistique (suivi APRÈS validation d'une demande —
    commande, réception, entrée en stock, sortie, projet…), configurable par
    le Responsable Achat et Logistique (RAL) : lui seul peut créer, modifier,
    supprimer, activer/désactiver et réordonner ces étapes.

    Remplace l'ancienne liste d'étapes figée en Python (LOGISTICS_ORDER_BY_TYPE) :
    UnifiedRequest.logistics_status n'est plus contraint à un `choices` fixe,
    il référence simplement le `code` d'une étape définie ici. Le circuit de
    VALIDATION (UnifiedRequest.status, DOP/DG/RAL selon le rôle du demandeur)
    reste un système totalement séparé et n'est jamais concerné par ce
    modèle — le circuit logistique ne démarre qu'une fois la demande validée
    (voir UnifiedRequest.advance_logistics).
    """
    request_type = models.CharField(max_length=20, choices=UnifiedRequest.REQUEST_TYPE_CHOICES)
    code         = models.SlugField(max_length=30, help_text="Identifiant technique, ex. reception_magasin")
    label        = models.CharField(max_length=100, verbose_name='Libellé affiché')
    order        = models.PositiveIntegerField(default=0, verbose_name='Position dans le circuit')
    is_reception_stage = models.BooleanField(
        default=False, verbose_name='Étape de réception',
        help_text="Déclenche l'entrée en stock (achat) ou la confirmation chantier (sortie)."
    )
    is_closing_stage = models.BooleanField(default=False, verbose_name='Étape de clôture')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['request_type', 'order', 'id']
        unique_together     = [('request_type', 'code')]
        verbose_name        = 'Étape du circuit logistique'
        verbose_name_plural = 'Étapes du circuit logistique'

    def __str__(self):
        return f"[{self.get_request_type_display()}] {self.order}. {self.label}"


class RALBudget(models.Model):
    """
    Budget annuel du Responsable Achat et Logistique (RAL) : créé et modifié
    exclusivement par l'Admin (DG) ; visible uniquement par le RAL et le DG
    (voir RALBudgetViewSet). Le RAL ne peut jamais le modifier lui-même.

    À 85% consommé, la création de nouvelles demandes d'achat par le RAL est
    automatiquement bloquée (voir UnifiedRequestViewSet.perform_create) tant
    que le DG n'a pas augmenté le budget ou explicitement débloqué le compte.
    """
    year            = models.PositiveIntegerField(unique=True, verbose_name='Année')
    montant_annuel  = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Budget annuel (FCFA)')
    is_manually_unblocked = models.BooleanField(
        default=False, verbose_name='Débloqué manuellement par le DG',
        help_text=(
            "Permet au RAL de continuer à créer des demandes d'achat malgré "
            f"le seuil de {RAL_BUDGET_BLOCK_THRESHOLD_PERCENT}% atteint."
        )
    )
    threshold_notified_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Empêche de renotifier le DG à chaque nouvelle demande une fois le seuil déjà signalé."
    )
    created_by      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='ral_budgets_created'
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-year']
        verbose_name        = 'Budget annuel RAL'
        verbose_name_plural = 'Budgets annuels RAL'

    def __str__(self):
        return f"Budget RAL {self.year} — {self.montant_annuel} FCFA"

    @property
    def montant_consomme(self):
        """Somme des demandes d'achat du RAL réellement EXÉCUTÉES cette
        année-là — une simple validation ne consomme jamais le budget. Pour
        un achat, `status` ne passe à 'executee' qu'à l'exécution par le
        Responsable Financier (voir execute_financial, Évolution 7) — jamais
        avant, et indépendamment de la réception magasin qui suit."""
        requests_qs = UnifiedRequest.objects.filter(
            request_type=RAL_BUDGET_REQUEST_TYPE,
            requested_by__role=ROLE_RAL,
            status=REQUEST_STATUS_EXECUTED,
            created_at__year=self.year,
        ).prefetch_related('items')
        total = 0
        for req in requests_qs:
            for item in req.items.all():
                if item.unit_price is not None:
                    total += float(item.quantity) * float(item.unit_price)
        return round(total, 2)

    @property
    def montant_restant(self):
        return round(float(self.montant_annuel) - self.montant_consomme, 2)

    @property
    def pourcentage_consomme(self):
        if not self.montant_annuel or float(self.montant_annuel) == 0:
            return 0
        return round((self.montant_consomme / float(self.montant_annuel)) * 100, 1)

    @property
    def is_threshold_reached(self):
        return self.pourcentage_consomme >= RAL_BUDGET_BLOCK_THRESHOLD_PERCENT

    @property
    def is_creation_blocked(self):
        """Bloque la création de nouvelles demandes d'achat du RAL : seuil de
        85% atteint et le DG n'a pas explicitement débloqué le compte."""
        return self.is_threshold_reached and not self.is_manually_unblocked