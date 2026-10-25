from django.db import models
from apps.accounts.models import User
from gertrack.business_rules import (
    NOTIF_TYPE_BUDGET_RAL_SEUIL, NOTIF_TYPE_PROJECT_BUDGET_BLOQUE,
    NOTIF_TYPE_A_EXECUTER_FINANCIER, NOTIF_TYPE_EXECUTEE_FINANCIEREMENT,
)


class Notification(models.Model):

    CATEGORY_CHOICES = [
        ('achat',   'Achat'),
        ('stock',   'Stock'),
        ('projet',  'Projet'),
        ('systeme', 'Système'),
    ]

    TYPE_CHOICES = [
        # Achats
        ('demande_soumise',  'Demande soumise'),
        ('demande_validee',  'Demande validée'),
        ('demande_refusee',  'Demande refusée'),
        ('demande_executee', 'Demande exécutée'),
        # Stock
        ('stock_faible',     'Stock faible'),
        ('stock_rupture',    'Rupture de stock'),
        # Projets
        ('budget_depasse',   'Dépassement budget'),
        ('echeance_proche',  'Échéance proche'),
        (NOTIF_TYPE_BUDGET_RAL_SEUIL, 'Seuil budget RAL atteint'),
        (NOTIF_TYPE_PROJECT_BUDGET_BLOQUE, 'Budget projet bloqué'),
        (NOTIF_TYPE_A_EXECUTER_FINANCIER, 'Demande à exécuter (Financier)'),
        (NOTIF_TYPE_EXECUTEE_FINANCIEREMENT, 'Demande exécutée financièrement'),
        # Administration
        ('demande_admin_soumise', 'Demande administrative soumise'),
        ('demande_admin_validee', 'Demande administrative validée'),
        ('demande_admin_refusee', 'Demande administrative refusée'),
        ('compte_cree',           'Compte créé'),
        # Logistique (Phase F — §7/§8)
        ('commande_arrivee',    'Commande arrivée'),
        ('commande_en_retard',  'Commande en retard'),
        ('livraison_chantier',  'Livraison chantier'),
    ]

    recipient  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Destinataire'
    )
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    notif_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=150)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)

    # Lien optionnel vers l'objet source
    link       = models.CharField(max_length=200, blank=True)
    object_id  = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'[{self.get_notif_type_display()}] → {self.recipient.username}'