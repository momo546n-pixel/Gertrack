# Migration volontairement limitée aux champs de blocage automatique du
# budget projet (Évolution 6) — le `makemigrations` automatique regroupait
# aussi une dérive de schéma préexistante et sans rapport sur Task/
# WeeklyReport/WeeklyTaskDetail (déjà signalée par Django avant cette
# évolution, non liée à ce travail) ; on ne la fait pas rentrer ici pour
# rester strictement sur le périmètre de cette évolution.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('operations', '0002_task_comment_task_sub_activity_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='budget_block_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='budget_blocked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='budget_unblocked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='budget_unblocked_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='projects_budget_unblocked', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='project',
            name='is_budget_blocked',
            field=models.BooleanField(default=False, verbose_name='Budget bloqué'),
        ),
    ]
