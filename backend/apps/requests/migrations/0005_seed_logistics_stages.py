# Recrée, sous forme de données, les étapes du circuit logistique qui
# étaient jusqu'ici figées en dur dans models.py (LOGISTICS_ORDER_BY_TYPE) —
# aucune demande existante n'est affectée : les codes stockés dans
# UnifiedRequest.logistics_status restent identiques, seule leur définition
# (libellé, ordre, étape de réception/clôture) devient éditable par le RAL.
from django.db import migrations

SEED_STAGES = [
    # request_type, code,                      label,                     order, is_reception, is_closing
    ('achat',  'commande_envoyee',        'Commande envoyée',        0, False, False),
    ('achat',  'en_attente_fournisseur',  'En attente fournisseur',  1, False, False),
    ('achat',  'livraison_partielle',     'Livraison partielle',     2, False, False),
    ('achat',  'livraison_complete',      'Livraison complète',      3, False, False),
    ('achat',  'reception_magasin',       'Réception magasin',       4, True,  False),
    ('achat',  'cloturee',                'Clôturée',                5, False, True),
    ('sortie', 'preparation',             'Préparation',             0, False, False),
    ('sortie', 'expedition',              'Expédition',              1, False, False),
    ('sortie', 'en_transit',              'En transit',              2, False, False),
    ('sortie', 'reception_chantier',      'Réception chantier',      3, True,  False),
    ('sortie', 'cloture_sortie',          'Clôturée',                4, False, True),
]


def seed_stages(apps, schema_editor):
    LogisticsStage = apps.get_model('requests', 'LogisticsStage')
    for request_type, code, label, order, is_reception, is_closing in SEED_STAGES:
        LogisticsStage.objects.update_or_create(
            request_type=request_type, code=code,
            defaults={
                'label': label, 'order': order,
                'is_reception_stage': is_reception,
                'is_closing_stage': is_closing,
                'is_active': True,
            },
        )


def unseed_stages(apps, schema_editor):
    LogisticsStage = apps.get_model('requests', 'LogisticsStage')
    codes_by_type = {}
    for request_type, code, *_ in SEED_STAGES:
        codes_by_type.setdefault(request_type, []).append(code)
    for request_type, codes in codes_by_type.items():
        LogisticsStage.objects.filter(request_type=request_type, code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0004_alter_unifiedrequest_logistics_status_logisticsstage'),
    ]

    operations = [
        migrations.RunPython(seed_stages, unseed_stages),
    ]
