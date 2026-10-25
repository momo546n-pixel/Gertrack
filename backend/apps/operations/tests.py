from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, User
from apps.notifications.models import Notification
from apps.products.models import Product
from apps.requests.models import RequestItem, UnifiedRequest

from .models import Project, WeeklyReport


class ProjectPermissionScopingTests(APITestCase):
    """
    Régression : le compte d'un magasin ne doit jamais voir les projets ni
    leurs budgets (ProjectViewSet.get_queryset ne traitait que le rôle
    'stock' — le rôle 'magasinier' passait au travers et voyait tout).
    """

    url = '/api/operations/projects/'

    def setUp(self):
        self.dg          = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.chef_ops    = User.objects.create_user(username='ops', password='pass', role=User.ROLE_OPS_CHIEF)
        self.pm          = User.objects.create_user(username='pm1', password='pass', role=User.ROLE_PM)
        self.other_pm    = User.objects.create_user(username='pm2', password='pass', role=User.ROLE_PM)
        self.magasinier  = User.objects.create_user(username='mag1', password='pass', role=User.ROLE_MAGASINIER)
        self.stock       = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)

        self.project = Project.objects.create(
            code='PRJ-TEST', name='Projet Test', project_manager=self.pm,
            budget=1000000,
        )

    def test_magasinier_sees_no_projects(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 0)

    def test_magasinier_cannot_retrieve_project_directly(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.get(f'{self.url}{self.project.id}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_stock_sees_no_projects(self):
        self.client.force_authenticate(self.stock)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 0)

    def test_pm_sees_only_own_project(self):
        self.client.force_authenticate(self.other_pm)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 0)

    def test_dg_sees_all_projects_with_budget(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get('results', res.data)
        self.assertEqual(len(data), 1)
        self.assertIn('budget', data[0])

    def test_non_assigned_pm_cannot_create_weekly_report(self):
        # get_queryset() scope à project_manager=user pour un PM : un projet
        # qui n'est pas le sien est introuvable (404) avant même d'atteindre
        # le contrôle de permission explicite de l'action — comportement
        # volontaire déjà établi ailleurs dans ce projet (ne fuite pas
        # l'existence de la ressource).
        self.client.force_authenticate(self.other_pm)
        res = self.client.post(f'{self.url}{self.project.id}/weekly-report/', {
            'week_number': 1, 'year': 2026,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_dg_cannot_create_weekly_report_for_others_project(self):
        # Le DG voit tous les projets (get_queryset ne le restreint pas) mais
        # ne doit pas pouvoir créer un rapport hebdomadaire à la place du
        # Chef de Projet assigné — ici le contrôle de permission explicite
        # s'applique bien puisque get_object() réussit.
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{self.project.id}/weekly-report/', {
            'week_number': 1, 'year': 2026,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class ProjectBudgetAutoBlockTests(APITestCase):
    """
    Évolution 6 — blocage automatique du budget projet : si le budget
    consommé atteint le seuil (85% par défaut, voir
    PROJECT_BUDGET_BLOCK_THRESHOLD_PERCENT) ET que l'avancement réel est en
    retard par rapport au dernier rapport hebdomadaire
    (WeeklyReport.progress_gap < 0), le projet est automatiquement bloqué —
    figé jusqu'au déblocage manuel du DG — et plus aucune nouvelle demande
    ne peut y être liée.
    """

    url = '/api/operations/projects/'

    def setUp(self):
        self.dg        = User.objects.create_user(username='dg_pb', password='pass', role=User.ROLE_DG)
        self.pm        = User.objects.create_user(username='pm_pb', password='pass', role=User.ROLE_PM)
        self.mag       = User.objects.create_user(username='mag_pb', password='pass', role=User.ROLE_MAGASINIER)
        self.stock     = User.objects.create_user(username='stock_pb', password='pass', role=User.ROLE_STOCK)
        self.financier = User.objects.create_user(username='financier_pb', password='pass', role=User.ROLE_FINANCIAL)
        self.project = Project.objects.create(
            code='PRJ-PB', name='Projet Budget Bloqué', project_manager=self.pm,
            budget=Decimal('1000'), status=Project.STATUS_ACTIVE,
        )
        self.product = Product.objects.create(
            code='PRD-PB', designation='Produit PB', unit='pcs',
            stock_actuel=Decimal('50'), stock_securite=Decimal('5'),
        )

    def _validate_achat(self, unit_price):
        """S'arrête à la validation — ne consomme rien (Évolution 7) : utile
        pour prouver qu'une simple validation ne déclenche jamais le blocage
        automatique, quel que soit le montant."""
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.pm, validation_type='dg_only', project=self.project,
        )
        RequestItem.objects.create(
            request=req, product=self.product, quantity=Decimal('1'), unit_price=Decimal(unit_price),
        )
        self.client.force_authenticate(self.pm)
        res = self.client.post(f'/api/requests/{req.id}/submit/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        # Le demandeur est un Chef de Projet : l'étape finale est réservée
        # au Responsable Achat et Logistique, pas au DG (voir
        # UnifiedRequestViewSet._can_act_at_dg_stage).
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'/api/requests/{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        return req

    def _validate_and_execute_achat(self, unit_price):
        """Va jusqu'au bout : validation PUIS exécution financière
        (Évolution 7) — c'est cette dernière étape, jamais la validation
        seule, qui consomme réellement le budget projet et peut déclencher
        le blocage automatique."""
        req = self._validate_achat(unit_price)
        self.client.force_authenticate(self.financier)
        res = self.client.post(f'/api/requests/{req.id}/execute-financial/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        return req

    def _add_late_report(self, week=1):
        return WeeklyReport.objects.create(
            project=self.project, week_number=week, year=timezone.now().year,
            report_date=timezone.now().date(),
            global_progress_snapshot=Decimal('20'), planned_progress=Decimal('50'),  # gap = -30 (en retard)
        )

    def _add_ontrack_report(self, week=1):
        return WeeklyReport.objects.create(
            project=self.project, week_number=week, year=timezone.now().year,
            report_date=timezone.now().date(),
            global_progress_snapshot=Decimal('60'), planned_progress=Decimal('50'),  # gap = +10 (dans les temps)
        )

    def test_no_block_without_weekly_report(self):
        self._validate_and_execute_achat('900')  # 90% consommé
        self.project.refresh_from_db()
        self.assertGreaterEqual(self.project.budget_pourcentage, 85)
        self.assertFalse(self.project.is_budget_blocked)

    def test_no_block_when_on_schedule(self):
        self._add_ontrack_report()
        self._validate_and_execute_achat('900')
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_budget_blocked)

    def test_no_block_when_below_threshold_even_if_late(self):
        self._add_late_report()
        self._validate_and_execute_achat('300')  # 30% seulement
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_budget_blocked)

    # ── Évolution 7 : la validation seule ne consomme et ne bloque jamais ────
    def test_validation_alone_never_triggers_block_even_at_threshold(self):
        """Même à 90% (si elle était exécutée) et avec un rapport en retard,
        une demande simplement VALIDÉE (jamais exécutée) ne doit jamais
        déclencher le blocage — voir Project.budget_consomme, désormais basé
        exclusivement sur 'executee'."""
        self._add_late_report()
        self._validate_achat('900')  # validée seulement, jamais exécutée
        self.project.refresh_from_db()
        self.assertEqual(self.project.budget_consomme, 0.0)
        self.assertFalse(self.project.is_budget_blocked)

    def test_auto_block_triggered_on_achat_execution(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')  # 90% + en retard
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_budget_blocked)
        self.assertIsNotNone(self.project.budget_blocked_at)
        self.assertTrue(self.project.budget_block_reason)

    def test_auto_block_notifies_dg_once(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')
        self.assertEqual(
            Notification.objects.filter(recipient=self.dg, notif_type='project_budget_bloque').count(), 1
        )

    def test_auto_block_logs_audit(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')
        self.assertTrue(
            AuditLog.objects.filter(
                model_name='Project', object_id=str(self.project.id),
                description__icontains='bloqué automatiquement',
            ).exists()
        )

    def test_block_prevents_new_request_creation(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')  # déclenche le blocage
        self.client.force_authenticate(self.mag)
        res = self.client.post('/api/requests/', {
            'request_type': 'entree', 'project': self.project.id,
            'items': [{'product': self.product.id, 'quantity': '1'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_block_is_sticky_even_if_budget_increased(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_budget_blocked)

        # Le DG augmente le budget — la consommation retombe sous le seuil,
        # mais le blocage reste figé (pas de déblocage automatique).
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.project.id}/', {'budget': '100000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.project.refresh_from_db()
        self.assertLess(self.project.budget_pourcentage, 85)
        self.assertTrue(self.project.is_budget_blocked)  # toujours bloqué

    def test_dg_can_unblock(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{self.project.id}/unblock-budget/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_budget_blocked)
        self.assertEqual(self.project.budget_unblocked_by_id, self.dg.id)

    def test_non_dg_cannot_unblock(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')
        self.client.force_authenticate(self.pm)
        res = self.client.post(f'{self.url}{self.project.id}/unblock-budget/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unblock_lifts_creation_block(self):
        self._add_late_report()
        self._validate_and_execute_achat('900')
        self.client.force_authenticate(self.dg)
        self.client.post(f'{self.url}{self.project.id}/unblock-budget/')

        self.client.force_authenticate(self.mag)
        res = self.client.post('/api/requests/', {
            'request_type': 'entree', 'project': self.project.id,
            'items': [{'product': self.product.id, 'quantity': '1'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_auto_block_triggered_via_weekly_report_creation(self):
        # Budget déjà >=85% (exécuté) mais aucun rapport pour l'instant — pas
        # de blocage.
        self._validate_and_execute_achat('900')
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_budget_blocked)

        # Un rapport en retard arrive ensuite — doit déclencher le blocage
        # via le point d'entrée weekly-report, pas seulement via un achat.
        self.client.force_authenticate(self.pm)
        res = self.client.post(f'{self.url}{self.project.id}/weekly-report/', {
            'week_number': 1, 'year': timezone.now().year,
            'report_date': str(timezone.now().date()),
            'global_progress_snapshot': '20', 'planned_progress': '50',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_budget_blocked)


class ProjectAuditTrailTests(APITestCase):
    """
    Évolution 8 — traçabilité avant/après sur Project.budget et
    Project.project_manager (voir gertrack.business_rules.
    AUDIT_TRACKED_FIELDS). Le log générique "Projet modifié" existant ne
    doit jamais disparaître ; les nouveaux événements structurés viennent
    en plus, jamais à la place.
    """

    url = '/api/operations/projects/'

    def setUp(self):
        self.dg  = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.pm1 = User.objects.create_user(username='pm1', password='pass', role=User.ROLE_PM)
        self.pm2 = User.objects.create_user(username='pm2', password='pass', role=User.ROLE_PM)
        self.project = Project.objects.create(
            code='PRJ-AUDIT', name='Projet Audit', status='en_cours',
            project_manager=self.pm1, budget=Decimal('100000'), created_by=self.dg,
        )

    def test_budget_change_creates_structured_log_without_removing_generic_one(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.project.id}/', {'budget': '150000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        generic = AuditLog.objects.filter(
            model_name='Project', object_id=str(self.project.id), field_name=''
        )
        self.assertTrue(generic.exists(), "le log générique 'Projet modifié' doit toujours exister")

        structured = AuditLog.objects.get(
            model_name='Project', object_id=str(self.project.id), field_name='budget'
        )
        self.assertEqual(structured.old_value, {'budget': 100000.0})
        self.assertEqual(structured.new_value, {'budget': 150000.0})

    def test_project_manager_change_creates_structured_log(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.project.id}/', {'project_manager': self.pm2.id}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        structured = AuditLog.objects.get(
            model_name='Project', object_id=str(self.project.id), field_name='project_manager'
        )
        self.assertEqual(structured.old_value, {'project_manager': 'pm1'})
        self.assertEqual(structured.new_value, {'project_manager': 'pm2'})

    def test_no_change_creates_no_structured_log(self):
        # Modifier un champ non suivi (ex. name) ne doit jamais créer de log
        # avant/après structuré — seulement le générique existant.
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.project.id}/', {'name': 'Nouveau nom'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertFalse(
            AuditLog.objects.filter(model_name='Project', object_id=str(self.project.id)).exclude(field_name='').exists()
        )
