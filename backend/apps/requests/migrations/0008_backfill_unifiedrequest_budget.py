# Relie chaque demande d'achat existante au budget annuel RAL de son année de
# création, s'il en existe un — pour que le nouveau champ `budget` (Évolution
# 4 : budget obligatoire) soit renseigné aussi largement que possible sur les
# données déjà en base. Sans impact sur les calculs de consommation
# (RALBudget.montant_consomme reste basé sur l'année, pas sur ce lien, pour
# ne jamais dépendre de la complétude de ce backfill) — cette migration est
# une amélioration de traçabilité, pas une correction requise pour que les
# calculs existants restent corrects.
from django.db import migrations


def backfill_budget(apps, schema_editor):
    UnifiedRequest = apps.get_model('requests', 'UnifiedRequest')
    RALBudget = apps.get_model('requests', 'RALBudget')

    budgets_by_year = {b.year: b for b in RALBudget.objects.all()}
    if not budgets_by_year:
        return

    achats = UnifiedRequest.objects.filter(request_type='achat', budget__isnull=True)
    for req in achats:
        budget = budgets_by_year.get(req.created_at.year)
        if budget is not None:
            req.budget = budget
            req.save(update_fields=['budget'])


def noop_reverse(apps, schema_editor):
    # Pas de retour en arrière significatif : on ne fait que relâcher le lien,
    # ce qui n'affecte aucun calcul (voir docstring du module).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0007_unifiedrequest_budget'),
    ]

    operations = [
        migrations.RunPython(backfill_budget, noop_reverse),
    ]
