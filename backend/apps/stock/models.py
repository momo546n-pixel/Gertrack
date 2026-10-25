from django.db import models
from django.core.validators import MinValueValidator
from apps.products.models import Product
from apps.accounts.models import User


# ─────────────────────────────────────────────────────────────────────────────
# MAGASIN
# ─────────────────────────────────────────────────────────────────────────────

class Warehouse(models.Model):
    code        = models.CharField(max_length=20, unique=True)
    name        = models.CharField(max_length=100)
    location    = models.CharField(max_length=255, blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    # Chaque magasin possède directement son propre compte de connexion
    # (le "gérant") — relation strictement 1-1 : un compte ne peut gérer
    # qu'un seul magasin. Nullable uniquement pour permettre le SET_NULL en
    # cas de suppression du compte indépendamment du magasin (cas résiduel).
    manager     = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, unique=True,
        related_name='managed_warehouses',
        limit_choices_to={'role': 'magasinier'},
        verbose_name='Compte du magasin (gérant)',
    )
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['name']
        verbose_name        = 'Magasin'
        verbose_name_plural = 'Magasins'

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def products_count(self):
        return self.movements.values('product').distinct().count()

    @property
    def total_movements(self):
        return self.movements.count()


# ─────────────────────────────────────────────────────────────────────────────
# MOUVEMENT DE STOCK
# ─────────────────────────────────────────────────────────────────────────────

class StockMovement(models.Model):

    ENTRY      = 'entree'
    EXIT       = 'sortie'
    ADJUSTMENT = 'ajustement'

    MOVEMENT_TYPES = [
        (ENTRY,      'Entrée'),
        (EXIT,       'Sortie'),
        (ADJUSTMENT, 'Ajustement'),
    ]

    ORIGIN_PURCHASE = 'achat'
    ORIGIN_RETURN   = 'retour'
    ORIGIN_MANUAL   = 'manuel'

    ORIGIN_CHOICES = [
        (ORIGIN_PURCHASE, 'Bon de commande'),
        (ORIGIN_RETURN,   'Retour'),
        (ORIGIN_MANUAL,   'Saisie manuelle'),
    ]

    product       = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='movements'
    )
    warehouse     = models.ForeignKey(
        'Warehouse', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movements',
        verbose_name='Magasin'
    )
    movement_type = models.CharField(max_length=15, choices=MOVEMENT_TYPES)
    quantity      = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock_before  = models.DecimalField(max_digits=12, decimal_places=2)
    stock_after   = models.DecimalField(max_digits=12, decimal_places=2)
    origin        = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default=ORIGIN_MANUAL)
    origin_ref    = models.CharField(max_length=50, blank=True)
    destination   = models.CharField(max_length=100, blank=True)
    notes         = models.TextField(blank=True)
    date          = models.DateField()
    created_by    = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-date', '-created_at']
        verbose_name        = 'Mouvement de stock'
        verbose_name_plural = 'Mouvements de stock'

    def __str__(self):
        return f"[{self.get_movement_type_display()}] {self.product.code} — {self.quantity} le {self.date}"

    def save(self, *args, **kwargs):
        is_new = not self.pk

        if is_new:
            product = self.product
            self.stock_before = product.stock_actuel

            # Une entrée/sortie à quantité nulle ou négative n'a pas de sens
            # métier et, pour la sortie, contournerait silencieusement le
            # contrôle de stock insuffisant ci-dessous (une quantité négative
            # ferait passer le test "stock_actuel - quantity < 0").
            if self.movement_type in (self.ENTRY, self.EXIT) and self.quantity <= 0:
                raise ValueError("La quantité doit être strictement positive pour une entrée ou une sortie.")

            if self.movement_type == self.ENTRY:
                product.stock_actuel += self.quantity

            elif self.movement_type == self.EXIT:
                if product.stock_actuel - self.quantity < 0:
                    raise ValueError("Stock insuffisant — le stock ne peut pas être négatif.")
                product.stock_actuel -= self.quantity

            elif self.movement_type == self.ADJUSTMENT:
                if self.quantity < 0:
                    raise ValueError("La quantité d'ajustement ne peut pas être négative.")
                product.stock_actuel = self.quantity

            self.stock_after = product.stock_actuel
            product.save(update_fields=['stock_actuel', 'updated_at'])

        super().save(*args, **kwargs)

        # ── Alertes stock automatiques ────────────────────────────────────────
        if is_new:
            try:
                from apps.notifications.utils import (
                    notify_stock_faible,
                    notify_stock_rupture,
                )
                # Recharge le produit depuis la DB pour avoir le stock à jour
                product = Product.objects.get(pk=self.product_id)

                if product.stock_actuel <= 0:
                    notify_stock_rupture(product)
                elif product.stock_actuel <= product.stock_securite:
                    notify_stock_faible(product)

            except Exception as e:
                # Ne bloque jamais le mouvement même si la notif échoue
                print(f"[NOTIF ERROR stock alert] {e}")