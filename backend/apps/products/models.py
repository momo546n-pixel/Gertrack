from django.db import models


class Category(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_OK       = 'suffisant'
    STATUS_CRITIQUE = 'critique'
    STATUS_RUPTURE  = 'rupture'

    code            = models.CharField(max_length=20, unique=True, db_index=True)
    designation     = models.CharField(max_length=255)
    category        = models.ForeignKey(
                          Category,
                          on_delete=models.SET_NULL,
                          null=True, blank=True,
                          related_name='products'
                      )
    unit            = models.CharField(max_length=20, default='Unité')
    conditionnement = models.CharField(max_length=50, blank=True)
    stock_actuel    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_securite  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description     = models.TextField(blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.designation}"

    @property
    def stock_status(self):
        if self.stock_actuel <= 0:
            return self.STATUS_RUPTURE
        elif self.stock_actuel <= self.stock_securite:
            return self.STATUS_CRITIQUE
        return self.STATUS_OK

    @property
    def needs_reorder(self):
        return self.stock_actuel <= self.stock_securite