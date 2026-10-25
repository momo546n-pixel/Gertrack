from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.utils import timezone

from gertrack.business_rules import AUDIT_ACTION_DENIED, ROLE_FINANCIAL


class User(AbstractUser):
    ROLE_DG          = 'dg'
    ROLE_STOCK       = 'stock'
    ROLE_OPS_CHIEF   = 'chef_ops'
    ROLE_PM          = 'chef_projet'
    ROLE_MAGASINIER  = 'magasinier'
    ROLE_FINANCIAL   = ROLE_FINANCIAL   # ← NOUVEAU (Évolution 7)

    ROLE_CHOICES = [
        (ROLE_DG,         'Directeur Général'),
        (ROLE_STOCK,      'Responsable Achat et Logistique'),
        (ROLE_OPS_CHIEF,  'Directrice des Opérations'),
        (ROLE_PM,         'Chef de Projet'),
        (ROLE_MAGASINIER, 'Magasinier'),
        (ROLE_FINANCIAL,  'Responsable Financier'),  # ← NOUVEAU
    ]

    role  = models.CharField(max_length=15, choices=ROLE_CHOICES, default=ROLE_STOCK)
    phone = models.CharField(max_length=20, blank=True)

    @property
    def is_dg(self):
        return self.role == self.ROLE_DG

    @property
    def is_stock_manager(self):
        return self.role == self.ROLE_STOCK

    @property
    def is_ops_chief(self):
        return self.role == self.ROLE_OPS_CHIEF

    @property
    def is_project_manager(self):
        return self.role == self.ROLE_PM

    @property
    def is_magasinier(self):
        return self.role == self.ROLE_MAGASINIER

    @property
    def is_financial_officer(self):                   # ← NOUVEAU (Évolution 7)
        return self.role == self.ROLE_FINANCIAL

    @property
    def can_manage_operations(self):
        return self.role in [
            self.ROLE_DG,
            self.ROLE_OPS_CHIEF,
            self.ROLE_PM,
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class AuditLog(models.Model):
    ACTION_CREATE   = 'CREATE'
    ACTION_UPDATE   = 'UPDATE'
    ACTION_DELETE   = 'DELETE'
    ACTION_VALIDATE = 'VALIDATE'
    ACTION_REFUSE   = 'REFUSE'
    ACTION_LOGIN    = 'LOGIN'
    ACTION_LOGOUT   = 'LOGOUT'
    # Distinct de ACTION_REFUSE (refus métier légitime, ex. DG qui refuse une
    # demande) : une tentative bloquée par une garde technique — double
    # exécution, étape déjà atteinte — n'est pas une décision humaine, c'est
    # une protection d'intégrité des données. Les séparer évite de polluer
    # l'historique des vrais refus métier avec des doubles-clics/retries.
    # Valeur définie dans gertrack/business_rules.py (réutilisable partout
    # sans duplication — voir apps.requests.models/views).
    ACTION_DENIED   = AUDIT_ACTION_DENIED
    # Distinct de ACTION_VALIDATE (validation DOP/DG, autorise l'achat) et de
    # ACTION_UPDATE (générique) : l'exécution financière est un événement
    # métier à part entière (Évolution 7) — c'est elle qui consomme
    # réellement le budget, pas la validation. Voir
    # UnifiedRequest.execute_financial.
    ACTION_EXECUTE  = 'EXECUTE'

    ACTION_CHOICES = [
        (ACTION_CREATE,   'Création'),
        (ACTION_UPDATE,   'Modification'),
        (ACTION_DELETE,   'Suppression'),
        (ACTION_VALIDATE, 'Validation'),
        (ACTION_REFUSE,   'Refus'),
        (ACTION_LOGIN,    'Connexion'),
        (ACTION_LOGOUT,   'Déconnexion'),
        (ACTION_DENIED,   'Tentative refusée'),
        (ACTION_EXECUTE,  'Exécution financière'),
    ]

    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name  = models.CharField(max_length=50)
    object_id   = models.CharField(max_length=50, blank=True, db_index=True)
    description = models.TextField()
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    # ── Avant / Après structuré (Évolution 8) ───────────────────────────────
    # Réservé volontairement à une courte liste de champs métier sensibles
    # (voir gertrack.business_rules.AUDIT_TRACKED_FIELDS) — pas un mécanisme
    # générique "tout changement de tout champ". Vides pour tout événement
    # antérieur à cette évolution : aucun backfill, aucun parsing du texte
    # libre des anciennes lignes (description reste la seule source pour
    # elles). old_value/new_value acceptent un objet JSON (ex.
    # {"budget": 150000}) plutôt qu'une valeur scalaire brute, pour ne pas
    # nécessiter de nouvelle migration le jour où plusieurs champs devront
    # être tracés dans le même événement.
    field_name  = models.CharField(max_length=100, blank=True)
    old_value   = models.JSONField(null=True, blank=True)
    new_value   = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['model_name', 'object_id'], name='auditlog_model_object_idx'),
        ]

    def __str__(self):
        return f"[{self.action}] {self.model_name} — {self.user} — {self.created_at:%d/%m/%Y %H:%M}"

    @classmethod
    def log(cls, user, action, model_name, obj_id='', description='', request=None,
             field_name='', old_value=None, new_value=None):
        """
        Enregistre une action du journal d'activité. L'adresse IP est extraite
        automatiquement de la requête HTTP en cours (via CurrentRequestMiddleware)
        si `request` n'est pas explicitement fourni — la quasi-totalité des
        appels n'ont donc rien à changer pour bénéficier du suivi IP.

        `field_name`/`old_value`/`new_value` sont optionnels (Évolution 8) —
        tous les appels existants qui ne les fournissent pas continuent de
        créer une ligne identique à avant, `old_value`/`new_value` restant
        `None`. Réservés à la courte liste de champs métier sensibles définie
        dans gertrack.business_rules.AUDIT_TRACKED_FIELDS.
        """
        from .middleware import get_current_request, get_client_ip
        ip_address = get_client_ip(request or get_current_request())
        return cls.objects.create(
            user=user, action=action, model_name=model_name,
            object_id=str(obj_id), description=description,
            ip_address=ip_address,
            field_name=field_name, old_value=old_value, new_value=new_value,
        )


# ─────────────────────────────────────────────────────────────────────────────
# DEMANDE ADMINISTRATIVE
#
# Modèle générique réutilisable pour les demandes de création/suppression de
# ressources qui doivent obligatoirement être validées par le DG avant
# d'exister réellement (magasin créé par le Responsable Achat et Logistique, chef de projet
# créé par le DOP, etc.). Le "payload" ne contient jamais de mot de passe :
# pour toute création de compte (magasin ou chef de projet), le mot de passe
# est fourni par le DG au moment de l'approbation, jamais par l'auteur de la
# demande à la soumission (voir AdminRequestSerializer.validate).
# ─────────────────────────────────────────────────────────────────────────────

class AdminRequest(models.Model):

    TYPE_WAREHOUSE_CREATION = 'creation_magasin'
    TYPE_WAREHOUSE_DELETION = 'suppression_magasin'
    TYPE_PM_CREATION        = 'creation_chef_projet'
    TYPE_PM_DELETION        = 'suppression_chef_projet'

    TYPE_CHOICES = [
        (TYPE_WAREHOUSE_CREATION, 'Création de magasin'),
        (TYPE_WAREHOUSE_DELETION, 'Suppression de magasin'),
        (TYPE_PM_CREATION,        'Création de chef de projet'),
        (TYPE_PM_DELETION,        'Suppression de chef de projet'),
    ]

    STATUS_PENDING  = 'en_attente'
    STATUS_APPROVED = 'validee'
    STATUS_REJECTED = 'refusee'

    STATUS_CHOICES = [
        (STATUS_PENDING,  'En attente'),
        (STATUS_APPROVED, 'Validée'),
        (STATUS_REJECTED, 'Refusée'),
    ]

    reference    = models.CharField(max_length=30, unique=True, blank=True)
    request_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    payload      = models.JSONField(default=dict, blank=True)
    status       = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)

    requested_by = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='admin_requests_made',
    )
    reviewed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admin_requests_reviewed',
    )
    reviewed_at    = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True)

    # Traçabilité vers la ressource effectivement créée après validation
    result_model     = models.CharField(max_length=50, blank=True)
    result_object_id  = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Demande administrative'
        verbose_name_plural = 'Demandes administratives'

    def __str__(self):
        return f"{self.reference} — {self.get_request_type_display()}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        year  = timezone.now().year
        count = AdminRequest.objects.filter(created_at__year=year).count() + 1
        return f"REQ-ADM-{year}-{count:04d}"

    # ── Workflow ──────────────────────────────────────────────────────────────
    def approve(self, reviewer, comment='', **extra):
        if self.status != self.STATUS_PENDING:
            raise ValueError("Cette demande a déjà été traitée.")

        # Fixé avant l'exécution : les méthodes de création ci-dessous
        # peuvent s'appuyer sur self.reviewed_by.
        self.reviewed_by    = reviewer
        self.reviewed_at    = timezone.now()
        self.review_comment = comment

        with transaction.atomic():
            if self.request_type == self.TYPE_WAREHOUSE_CREATION:
                result_model, result_id = self._approve_warehouse_creation(**extra)
            elif self.request_type == self.TYPE_WAREHOUSE_DELETION:
                result_model, result_id = self._approve_warehouse_deletion()
            elif self.request_type == self.TYPE_PM_CREATION:
                result_model, result_id = self._approve_pm_creation(**extra)
            elif self.request_type == self.TYPE_PM_DELETION:
                result_model, result_id = self._approve_pm_deletion()
            else:
                raise ValueError("Type de demande non pris en charge.")

            self.status           = self.STATUS_APPROVED
            self.result_model     = result_model
            self.result_object_id = result_id
            self.save()
        return self

    def reject(self, reviewer, comment=''):
        if self.status != self.STATUS_PENDING:
            raise ValueError("Cette demande a déjà été traitée.")
        self.status         = self.STATUS_REJECTED
        self.reviewed_by    = reviewer
        self.reviewed_at    = timezone.now()
        self.review_comment = comment
        self.save()
        return self

    # ── Création effective (uniquement appelée depuis approve()) ─────────────
    def _approve_warehouse_creation(self, password=None, **_kwargs):
        from django.db import IntegrityError
        from apps.stock.models import Warehouse

        data = self.payload
        if not password:
            raise ValueError("Un mot de passe est requis pour créer le compte du magasin.")

        try:
            # Le mot de passe est défini par le DG au moment de la validation,
            # que la demande vienne du DG lui-même ou du Responsable Achat et Logistique.
            magasinier = User.objects.create_user(
                username   = data['username'],
                password   = password,
                first_name = data.get('first_name', ''),
                last_name  = data.get('last_name', ''),
                email      = data.get('account_email', ''),
                phone      = data.get('account_phone', ''),
                role       = User.ROLE_MAGASINIER,
            )

            warehouse = Warehouse.objects.create(
                code     = data['code'],
                name     = data['name'],
                location = data.get('location', ''),
                phone    = data.get('phone', ''),
                email    = data.get('email', ''),
                manager  = magasinier,
            )
        except IntegrityError as e:
            raise ValueError(f"Impossible de créer le magasin/compte : {e}")

        return ('Warehouse', warehouse.id)

    def _approve_warehouse_deletion(self):
        from apps.stock.models import Warehouse
        try:
            warehouse = Warehouse.objects.get(pk=self.payload.get('warehouse_id'))
        except Warehouse.DoesNotExist:
            raise ValueError("Le magasin visé par cette demande n'existe plus.")
        warehouse.is_active = False
        warehouse.save(update_fields=['is_active', 'updated_at'])
        return ('Warehouse', warehouse.id)

    def _approve_pm_creation(self, password=None, **_kwargs):
        from django.db import IntegrityError

        data = self.payload
        if not password:
            raise ValueError("Un mot de passe est requis pour créer le compte chef de projet.")

        try:
            pm = User.objects.create_user(
                username   = data['username'],
                password   = password,
                first_name = data.get('first_name', ''),
                last_name  = data.get('last_name', ''),
                email      = data.get('email', ''),
                phone      = data.get('phone', ''),
                role       = User.ROLE_PM,
            )
        except IntegrityError as e:
            raise ValueError(f"Impossible de créer le compte chef de projet : {e}")

        return ('User', pm.id)

    def _approve_pm_deletion(self):
        try:
            pm = User.objects.get(pk=self.payload.get('user_id'), role=User.ROLE_PM)
        except User.DoesNotExist:
            raise ValueError("Le chef de projet visé par cette demande n'existe plus.")
        pm.is_active = False
        pm.save(update_fields=['is_active'])
        return ('User', pm.id)