from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.operations.models import Project


class Command(BaseCommand):
    help = (
        "Notifie le DG et le Chef de Projet des projets actifs dont l'échéance "
        "approche ou est dépassée (§9 — notifications). Aucun planificateur "
        "n'est configuré dans ce projet : à exécuter quotidiennement via un "
        "cron / une tâche planifiée système en production."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=7,
            help="Fenêtre d'alerte en jours avant l'échéance (défaut : 7).",
        )

    def handle(self, *args, **options):
        from apps.notifications.utils import notify_echeance_proche

        window = options['days']
        today  = timezone.now().date()
        limit  = today + timedelta(days=window)

        projects = Project.objects.filter(
            status__in=[Project.STATUS_ACTIVE, Project.STATUS_ON_HOLD],
            planned_end_date__isnull=False,
            planned_end_date__lte=limit,
        )

        count = 0
        for project in projects:
            days_remaining = (project.planned_end_date - today).days
            notify_echeance_proche(project, days_remaining)
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f"{count} projet(s) notifié(s) pour échéance proche ou dépassée."
        ))
