from django.db import migrations


def backfill_manager(apps, schema_editor):
    """
    Avant de supprimer WarehouseAccess (many-to-many hérité de l'ancien
    système), s'assure qu'aucun accès existant n'est perdu : si un magasin
    n'a pas de manager mais possède un WarehouseAccess, on le reporte sur
    Warehouse.manager (la nouvelle relation 1-1 qui fait foi désormais).
    """
    Warehouse       = apps.get_model('stock', 'Warehouse')
    WarehouseAccess = apps.get_model('stock', 'WarehouseAccess')

    for warehouse in Warehouse.objects.filter(manager__isnull=True):
        access = WarehouseAccess.objects.filter(warehouse=warehouse).order_by('granted_at').first()
        if access:
            warehouse.manager = access.user
            warehouse.save(update_fields=['manager'])


def noop_reverse(apps, schema_editor):
    pass  # irréversible : on ne recrée pas les WarehouseAccess supprimés


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0004_alter_stockmovement_options_warehouse_email_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_manager, noop_reverse),
    ]
