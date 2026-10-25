from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, User
from apps.notifications.models import Notification
from apps.operations.models import Project, WeeklyReport
from apps.products.models import Product
from apps.stock.models import Warehouse, StockMovement
from apps.suppliers.models import Supplier

from .models import UnifiedRequest, LogisticsStage, RALBudget, RequestItem, DuplicateExecutionError


class UnifiedRequestPermissionTests(APITestCase):
    """
    Vérifie la matrice de permissions par rôle introduite pour remplacer
    le module "Mouvements" par le circuit unique de demandes :
      - le magasinier est limité à entrée/sortie/ajustement et à son magasin
      - le chef de projet est limité à entrée/sortie et à ses propres projets
      - le Responsable Achat et Logistique (rôle 'stock') a les mêmes droits que le DG
        pour la consultation, mais chaque étape de validation (DOP, DG) est
        réservée au rôle qui en a la charge — pas de droit de substitution.
    """

    url = '/api/requests/'

    def setUp(self):
        self.dg = User.objects.create_user(
            username='dg', password='pass', role=User.ROLE_DG,
        )
        self.stock_manager = User.objects.create_user(
            username='stock', password='pass', role=User.ROLE_STOCK,
        )
        self.magasinier = User.objects.create_user(
            username='mag', password='pass', role=User.ROLE_MAGASINIER,
        )
        self.other_magasinier = User.objects.create_user(
            username='mag2', password='pass', role=User.ROLE_MAGASINIER,
        )
        self.chef_projet = User.objects.create_user(
            username='pm', password='pass', role=User.ROLE_PM,
        )
        self.dop = User.objects.create_user(
            username='dop', password='pass', role=User.ROLE_OPS_CHIEF,
        )
        self.other_pm = User.objects.create_user(
            username='pm2', password='pass', role=User.ROLE_PM,
        )

        self.warehouse       = Warehouse.objects.create(code='WH1', name='Magasin Principal', manager=self.magasinier)
        self.other_warehouse = Warehouse.objects.create(code='WH2', name='Autre Magasin', manager=self.other_magasinier)

        self.project       = Project.objects.create(
            code='PRJ-1', name='Projet Un', project_manager=self.chef_projet,
        )
        self.other_project = Project.objects.create(
            code='PRJ-2', name='Projet Deux', project_manager=self.other_pm,
        )

        self.supplier = Supplier.objects.create(name='Fournisseur Test')
        self.product  = Product.objects.create(
            code='PRD-1', designation='Produit test', unit='pcs',
            stock_actuel=Decimal('100'), stock_securite=Decimal('10'),
        )

    def _payload(self, request_type, **overrides):
        payload = {
            'request_type':    request_type,
            'validation_type': 'dg_only',
            'motif':           'Test',
            'items': [
                {'product': self.product.id, 'quantity': '5', 'unit_price': None, 'notes': ''},
            ],
        }
        payload.update(overrides)
        return payload

    # ── Magasinier ────────────────────────────────────────────────────────────
    def test_magasinier_cannot_create_achat_request(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(self.url, self._payload('achat'), format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_cannot_create_request_for_unauthorized_warehouse(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(
            self.url,
            self._payload('entree', warehouse=self.other_warehouse.id),
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_can_create_entree_for_own_warehouse(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(
            self.url,
            self._payload('entree', warehouse=self.warehouse.id),
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_dg_cannot_create_request(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.url, self._payload('achat'), format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_request_validation_type_is_forced_to_dg_only(self):
        # Même si le magasinier soumet "dop_then_dg", sa demande n'a qu'une
        # seule étape de validation, assurée par le Responsable Achat et Logistique.
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(
            self.url,
            self._payload('entree', warehouse=self.warehouse.id, validation_type='dop_then_dg'),
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        req = UnifiedRequest.objects.get(pk=res.data['id'])
        self.assertEqual(req.validation_type, 'dg_only')
        self.assertEqual(req.status, 'brouillon')

    # ── Chef de projet ────────────────────────────────────────────────────────
    def test_chef_projet_cannot_create_achat(self):
        self.client.force_authenticate(self.chef_projet)
        res = self.client.post(
            self.url, self._payload('achat', project=self.project.id), format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_chef_projet_must_provide_project(self):
        self.client.force_authenticate(self.chef_projet)
        res = self.client.post(self.url, self._payload('entree'), format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_chef_projet_cannot_create_for_foreign_project(self):
        self.client.force_authenticate(self.chef_projet)
        res = self.client.post(
            self.url,
            self._payload('sortie', project=self.other_project.id),
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_chef_projet_can_create_for_own_project(self):
        self.client.force_authenticate(self.chef_projet)
        res = self.client.post(
            self.url,
            self._payload('entree', project=self.project.id),
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_chef_projet_request_validation_type_is_forced_to_dop_then_dg(self):
        # Même si le chef de projet soumet "dg_only", sa demande passe
        # toujours par le DOP puis par le Responsable Achat et Logistique.
        self.client.force_authenticate(self.chef_projet)
        res = self.client.post(
            self.url,
            self._payload('entree', project=self.project.id, validation_type='dg_only'),
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        req = UnifiedRequest.objects.get(pk=res.data['id'])
        self.assertEqual(req.validation_type, 'dop_then_dg')

    # ── Responsable Achat et Logistique ─────────────────────────────────────────────────────
    def test_stock_role_sees_all_requests(self):
        UnifiedRequest.objects.create(request_type='sortie', requested_by=self.magasinier)
        UnifiedRequest.objects.create(request_type='entree', requested_by=self.chef_projet)
        self.client.force_authenticate(self.stock_manager)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 2)

    def test_stock_role_cannot_validate_dg_for_stock_own_request(self):
        # Demande soumise par le Responsable Achat et Logistique lui-même : seul le DG
        # valide l'étape finale, Stock ne peut pas se substituer au DG.
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.stock_manager,
            status='en_attente_dg', warehouse=self.warehouse,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.stock_manager)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dg')

    def test_dg_can_validate_dg_for_stock_own_request(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.stock_manager,
            status='en_attente_dg', warehouse=self.warehouse,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertEqual(req.status, 'executee')

    def test_validate_dg_cannot_execute_stock_movement_twice(self):
        """Double-clic / retry réseau sur validate-dg : la seconde tentative
        doit être rejetée, sans créer un second mouvement de stock, avec une
        trace dans l'AuditLog et sans aucune notification."""
        from apps.stock.models import StockMovement
        from apps.notifications.models import Notification
        from apps.accounts.models import AuditLog
        from .models import RequestItem
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.stock_manager,
            status='en_attente_dg', warehouse=self.warehouse,
        )
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movements_after_first = StockMovement.objects.filter(origin_ref=req.reference).count()
        self.assertGreater(movements_after_first, 0)
        notif_count_after_first = Notification.objects.count()

        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'encore'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        movements_after_second = StockMovement.objects.filter(origin_ref=req.reference).count()
        self.assertEqual(movements_after_first, movements_after_second)

        # Traçabilité : la tentative refusée est enregistrée dans l'AuditLog...
        denied_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_DENIED, model_name='UnifiedRequest', object_id=str(req.id),
        ).first()
        self.assertIsNotNone(denied_log)
        self.assertEqual(denied_log.user, self.dg)
        self.assertIn(req.reference, denied_log.description)
        # ... mais ne déclenche strictement aucune notification.
        self.assertEqual(Notification.objects.count(), notif_count_after_first)

    # ── Étape finale pour une demande de magasinier/chef de projet : réservée
    #    au Responsable Achat et Logistique, le DG ne peut plus s'y substituer ────────────────
    def test_stock_can_validate_dg_for_magasinier_request(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.magasinier,
            status='en_attente_dg', warehouse=self.warehouse,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.stock_manager)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'executee')

    def test_dg_cannot_validate_dg_for_magasinier_request(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.magasinier,
            status='en_attente_dg', warehouse=self.warehouse,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dg')

    def test_stock_can_validate_dg_for_chef_projet_request(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.chef_projet,
            status='en_attente_dg', project=self.project,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.stock_manager)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'executee')

    def test_dg_cannot_validate_dg_for_chef_projet_request(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.chef_projet,
            status='en_attente_dg', project=self.project,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dg')

    def test_dg_cannot_reject_dg_for_magasinier_request(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.magasinier,
            status='en_attente_dg', warehouse=self.warehouse,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/reject-dg/', {'comment': 'non'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dg')

    # ── Étape DOP : réservée au DOP et au Responsable Achat et Logistique, pas au DG ────────
    def test_dop_can_validate_dop(self):
        req = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.chef_projet,
            status='en_attente_dop', validation_type='dop_then_dg',
            warehouse=self.warehouse, project=self.project,
        )
        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{req.id}/validate-dop/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dg')

    def test_dg_cannot_validate_dop(self):
        req = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.chef_projet,
            status='en_attente_dop', validation_type='dop_then_dg',
            warehouse=self.warehouse, project=self.project,
        )
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/validate-dop/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dop')

    def test_dg_cannot_reject_dop(self):
        req = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.chef_projet,
            status='en_attente_dop', validation_type='dop_then_dg',
            warehouse=self.warehouse, project=self.project,
        )
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/reject-dop/', {'comment': 'non'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertEqual(req.status, 'en_attente_dop')

    # ── PDF réservé aux demandes d'achat ─────────────────────────────────────
    def test_pdf_forbidden_for_non_achat_request(self):
        req = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.magasinier,
            status='executee', warehouse=self.warehouse,
        )
        self.client.force_authenticate(self.stock_manager)
        res = self.client.get(f'{self.url}{req.id}/pdf/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_allowed_for_validated_achat_request(self):
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock_manager,
            status='validee',
        )
        from .models import RequestItem
        RequestItem.objects.create(
            request=req, product=self.product, quantity=Decimal('2'), unit_price=Decimal('100'),
        )
        self.client.force_authenticate(self.stock_manager)
        res = self.client.get(f'{self.url}{req.id}/pdf/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/pdf')


class LogisticsWorkflowTests(APITestCase):
    """
    Phase F V2.1 (§7 achats / §8 sorties) : le circuit logistique post-
    validation ne modifie jamais `status` (DOP/DG) ; il avance séparément
    via `logistics_status`, avec retard détecté automatiquement, et pour
    les sorties, la réception chantier ne peut être confirmée que par le
    Chef de Projet du projet concerné.
    """

    url = '/api/requests/'

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.dop   = User.objects.create_user(username='dop', password='pass', role=User.ROLE_OPS_CHIEF)
        self.pm    = User.objects.create_user(username='pm', password='pass', role=User.ROLE_PM)
        self.other_pm = User.objects.create_user(username='pm2', password='pass', role=User.ROLE_PM)

        self.warehouse = Warehouse.objects.create(code='WH1', name='Magasin Principal')
        self.supplier  = Supplier.objects.create(name='Fournisseur Test')
        self.project   = Project.objects.create(code='PRJ-LOG', name='Projet Log', project_manager=self.pm)
        self.product   = Product.objects.create(
            code='PRD-LOG', designation='Produit log', unit='pcs',
            stock_actuel=Decimal('100'), stock_securite=Decimal('5'),
        )

    def _achat(self, **overrides):
        # status='executee' directement : ces tests portent sur le circuit
        # LOGISTIQUE (post-exécution financière — Évolution 7), pas sur
        # l'exécution elle-même (voir FinancialExecutionTests). Le circuit
        # logistique n'accepte plus 'validee' comme point de départ.
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='executee',
            supplier=self.supplier, **overrides,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('10'), unit_price=Decimal('50'))
        return req

    def _sortie(self, **overrides):
        req = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.pm, status='executee',
            warehouse=self.warehouse, project=self.project, **overrides,
        )
        from .models import RequestItem
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('5'))
        return req

    # ── Achat ─────────────────────────────────────────────────────────────────
    def test_stock_can_advance_achat_through_full_cycle(self):
        req = self._achat()
        self.client.force_authenticate(self.stock)
        stages = ['commande_envoyee', 'en_attente_fournisseur', 'livraison_complete', 'reception_magasin', 'cloturee']
        for stage in stages:
            res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': stage}, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.logistics_status, 'cloturee')
        self.assertIsNotNone(req.date_livraison_reelle)

    def test_advance_logistics_with_date_string_payload_does_not_crash(self):
        """
        Régression : la date envoyée par le frontend (chaîne JSON, ex.
        "2026-06-01") doit être convertie en objet date avant d'être
        comparée dans `est_en_retard` — sinon TypeError (date vs str).
        """
        req = self._achat()
        self.client.force_authenticate(self.stock)
        res = self.client.post(
            f'{self.url}{req.id}/advance-logistics/',
            {'logistics_status': 'commande_envoyee', 'date_livraison_prevue': '2026-06-01'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertTrue(res.data['est_en_retard'])

    def test_reception_magasin_creates_stock_movement(self):
        req = self._achat()
        stock_before = self.product.stock_actuel
        self.client.force_authenticate(self.stock)
        self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'commande_envoyee'}, format='json')
        self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_magasin'}, format='json')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actuel, stock_before + Decimal('10'))

    def test_cannot_skip_backwards_in_logistics(self):
        req = self._achat(logistics_status='livraison_complete')
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'commande_envoyee'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delay_detected_automatically(self):
        import datetime
        past_date = datetime.date.today() - datetime.timedelta(days=5)
        req = self._achat(date_livraison_prevue=past_date, logistics_status='livraison_complete')
        self.assertTrue(req.est_en_retard)

    def test_not_delayed_once_closed(self):
        import datetime
        past_date = datetime.date.today() - datetime.timedelta(days=5)
        req = self._achat(date_livraison_prevue=past_date, logistics_status='cloturee')
        self.assertFalse(req.est_en_retard)

    def test_dop_cannot_advance_achat_logistics(self):
        # Le DOP ne voit même pas une demande d'achat validée qu'il n'a pas
        # lui-même soumise (get_queryset le restreint) : 404, pas 403 — mais
        # le résultat pratique est le même : accès refusé.
        req = self._achat()
        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'commande_envoyee'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ── Sortie ────────────────────────────────────────────────────────────────
    def test_requester_can_advance_sortie_up_to_transit(self):
        # _sortie() est demandée par self.pm : le suivi logistique (hors
        # réception chantier) est réservé à l'auteur de la demande.
        req = self._sortie()
        self.client.force_authenticate(self.pm)
        for stage in ['preparation', 'expedition', 'en_transit']:
            res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': stage}, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    def test_non_requester_stock_cannot_advance_sortie(self):
        req = self._sortie()
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'preparation'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_project_pm_can_confirm_site_reception(self):
        req = self._sortie(logistics_status='en_transit')

        # Le Responsable Achat et Logistique voit la demande (queryset non restreint) mais
        # se heurte au contrôle métier explicite : seul le CP du projet.
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_chantier'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Un autre chef de projet ne voit même pas cette demande (get_queryset
        # le restreint à ses propres demandes) : 404.
        self.client.force_authenticate(self.other_pm)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_chantier'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.pm)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_chantier'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        req.refresh_from_db()
        self.assertEqual(req.reception_confirmed_by, self.pm)
        self.assertIsNotNone(req.reception_confirmed_at)

    def test_dg_can_confirm_site_reception_as_override(self):
        req = self._sortie(logistics_status='en_transit')
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_chantier'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_sortie_reception_does_not_duplicate_stock_movement(self):
        """La sortie a déjà exécuté son mouvement de stock à la validation DG ;
        la réception chantier ne doit pas en recréer un second."""
        from apps.stock.models import StockMovement
        req = self._sortie(logistics_status='en_transit')
        movements_before = StockMovement.objects.filter(origin_ref=req.reference).count()
        self.client.force_authenticate(self.pm)
        self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_chantier'}, format='json')
        movements_after = StockMovement.objects.filter(origin_ref=req.reference).count()
        self.assertEqual(movements_before, movements_after)

    # ── Protection contre la double exécution ──────────────────────────────
    def test_achat_reception_cannot_be_executed_twice(self):
        """Double-clic / retry réseau : un second appel à 'reception_magasin'
        sur une demande déjà réceptionnée doit être rejeté, sans créer un
        second mouvement de stock (double consommation du budget RAL), avec
        une trace dans l'AuditLog et sans aucune notification."""
        from apps.stock.models import StockMovement
        from apps.notifications.models import Notification
        from apps.accounts.models import AuditLog
        req = self._achat()
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_magasin'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        movements_after_first = StockMovement.objects.filter(origin_ref=req.reference).count()
        self.assertGreater(movements_after_first, 0)
        notif_count_after_first = Notification.objects.count()

        # Second appel — identique, simulant un double-clic ou une nouvelle
        # tentative réseau après un timeout côté client.
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'reception_magasin'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        movements_after_second = StockMovement.objects.filter(origin_ref=req.reference).count()
        self.assertEqual(movements_after_first, movements_after_second)

        denied_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_DENIED, model_name='UnifiedRequest', object_id=str(req.id),
        ).first()
        self.assertIsNotNone(denied_log)
        self.assertEqual(denied_log.user, self.stock)
        self.assertIn(req.reference, denied_log.description)
        self.assertEqual(Notification.objects.count(), notif_count_after_first)

    def test_advance_logistics_rejects_resubmitting_same_stage(self):
        """Pas seulement la réception : toute étape déjà atteinte ne peut pas
        être renvoyée une seconde fois (pas seulement le retour en arrière)."""
        req = self._achat()
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'commande_envoyee'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        res = self.client.post(f'{self.url}{req.id}/advance-logistics/', {'logistics_status': 'commande_envoyee'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class LogisticsStageManagementTests(APITestCase):
    """
    Le circuit logistique (LogisticsStage) est configurable exclusivement
    par le Responsable Achat et Logistique (RAL) : créer, modifier,
    supprimer, activer/désactiver et réordonner les étapes. Aucun autre
    profil, DG compris, ne peut y toucher — le circuit de VALIDATION
    (UnifiedRequest.status) reste un système totalement séparé.
    """

    url = '/api/requests/logistics-stages/'

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.dop   = User.objects.create_user(username='dop', password='pass', role=User.ROLE_OPS_CHIEF)

    def test_ral_can_list_stages(self):
        self.client.force_authenticate(self.stock)
        res = self.client.get(f'{self.url}?request_type=achat')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = [s['code'] for s in res.data.get('results', res.data)]
        self.assertIn('reception_magasin', codes)
        self.assertIn('cloturee', codes)

    def test_dg_cannot_access_logistics_stages(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dop_cannot_access_logistics_stages(self):
        self.client.force_authenticate(self.dop)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_ral_can_create_stage(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, {
            'request_type': 'achat', 'code': 'douane', 'label': 'Dédouanement', 'order': 10,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_dg_cannot_create_stage(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.url, {
            'request_type': 'achat', 'code': 'douane', 'label': 'Dédouanement', 'order': 10,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_ral_can_update_stage_label(self):
        stage = LogisticsStage.objects.get(request_type='achat', code='commande_envoyee')
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'{self.url}{stage.id}/', {'label': 'Commande transmise'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        stage.refresh_from_db()
        self.assertEqual(stage.label, 'Commande transmise')

    def test_ral_can_deactivate_stage_in_use(self):
        """Désactiver une étape même utilisée par une demande en cours reste
        autorisé — seule la SUPPRESSION doit être bloquée."""
        stage = LogisticsStage.objects.get(request_type='achat', code='en_attente_fournisseur')
        UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='validee',
            logistics_status='en_attente_fournisseur',
        )
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'{self.url}{stage.id}/', {'is_active': False}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_ral_cannot_delete_stage_in_use(self):
        stage = LogisticsStage.objects.get(request_type='achat', code='livraison_partielle')
        UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='validee',
            logistics_status='livraison_partielle',
        )
        self.client.force_authenticate(self.stock)
        res = self.client.delete(f'{self.url}{stage.id}/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(LogisticsStage.objects.filter(pk=stage.id).exists())

    def test_ral_can_delete_unused_stage(self):
        stage = LogisticsStage.objects.create(
            request_type='achat', code='temp_stage', label='Temporaire', order=99,
        )
        self.client.force_authenticate(self.stock)
        res = self.client.delete(f'{self.url}{stage.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LogisticsStage.objects.filter(pk=stage.id).exists())

    def test_setting_new_reception_stage_clears_previous_one(self):
        old = LogisticsStage.objects.get(request_type='achat', code='reception_magasin')
        new = LogisticsStage.objects.get(request_type='achat', code='livraison_complete')
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'{self.url}{new.id}/', {'is_reception_stage': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        old.refresh_from_db()
        new.refresh_from_db()
        self.assertFalse(old.is_reception_stage)
        self.assertTrue(new.is_reception_stage)

    def test_reorder_stages(self):
        stages = list(LogisticsStage.objects.filter(request_type='sortie').order_by('order'))
        reversed_ids = [s.id for s in reversed(stages)]
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}reorder/', {
            'request_type': 'sortie', 'stage_ids': reversed_ids,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        reordered = list(LogisticsStage.objects.filter(request_type='sortie').order_by('order'))
        self.assertEqual([s.id for s in reordered], reversed_ids)

    def test_dop_cannot_reorder_stages(self):
        stages = list(LogisticsStage.objects.filter(request_type='sortie').order_by('order'))
        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}reorder/', {
            'request_type': 'sortie', 'stage_ids': [s.id for s in stages],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class RALBudgetTests(APITestCase):
    """
    Budget annuel du RAL : créé/modifié exclusivement par le DG, visible
    uniquement par le RAL et le DG. À 85% consommé, le RAL ne peut plus créer
    de nouvelle demande d'achat tant que le DG n'augmente pas le budget ou ne
    débloque pas le compte manuellement.

    Règle corrigée par le DG : une simple VALIDATION ne consomme jamais le
    budget — seule une demande réellement EXÉCUTÉE (réception magasin, donc
    `status == 'executee'`) compte. C'est le point d'entrée que reprendra le
    Responsable Financier (Évolution 7) sans rien changer ici.
    """

    url = '/api/requests/ral-budget/'

    def setUp(self):
        self.dg        = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock     = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.dop       = User.objects.create_user(username='dop', password='pass', role=User.ROLE_OPS_CHIEF)
        self.financier = User.objects.create_user(username='financier_ral', password='pass', role=User.ROLE_FINANCIAL)
        self.product = Product.objects.create(
            code='PRD-RAL', designation='Produit RAL', unit='pcs',
            stock_actuel=Decimal('100'), stock_securite=Decimal('5'),
        )
        self.year = timezone.now().year

    def _create_and_validate_achat(self, unit_price, quantity='1'):
        """Crée puis valide (étape DG) une demande d'achat du RAL — s'arrête
        AVANT l'exécution : `status` reste 'validee', ne consomme donc rien."""
        from .models import RequestItem
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, validation_type='dg_only',
        )
        RequestItem.objects.create(
            request=req, product=self.product, quantity=Decimal(quantity), unit_price=Decimal(unit_price),
        )
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'/api/requests/{req.id}/submit/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'/api/requests/{req.id}/validate-dg/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        return req

    def _create_and_execute_achat(self, unit_price, quantity='1'):
        """Va jusqu'au bout : validation DG PUIS exécution financière
        (Évolution 7) — c'est cette dernière étape, pas la réception
        magasin, qui pose désormais `status='executee'` et fait réellement
        consommer le budget RAL."""
        req = self._create_and_validate_achat(unit_price, quantity)
        self.client.force_authenticate(self.financier)
        res = self.client.post(f'/api/requests/{req.id}/execute-financial/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'executee')
        return req

    def test_dg_can_create_budget(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.url, {'year': self.year, 'montant_annuel': '1000000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_dg_can_update_budget_amount(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{budget.id}/', {'montant_annuel': '1500000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        budget.refresh_from_db()
        self.assertEqual(budget.montant_annuel, Decimal('1500000'))

    def test_ral_cannot_create_budget(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, {'year': self.year, 'montant_annuel': '1000000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_ral_can_view_budget(self):
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        self.client.force_authenticate(self.stock)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 1)

    def test_other_role_sees_no_budget(self):
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        self.client.force_authenticate(self.dop)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 0)

    def test_ral_cannot_update_budget(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'{self.url}{budget.id}/', {'montant_annuel': '2000000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── Règle corrigée : validation seule ne consomme jamais le budget ───────
    def test_validation_alone_does_not_consume_budget(self):
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_validate_achat(unit_price='900')  # validée, PAS exécutée
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        data = res.data.get('results', res.data)[0]
        self.assertEqual(data['montant_consomme'], 0.0)
        self.assertEqual(data['pourcentage_consomme'], 0)
        self.assertFalse(data['is_threshold_reached'])

    def test_consumption_computed_from_executed_achats_only(self):
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_execute_achat(unit_price='300')
        # Une seconde demande simplement validée ne doit rien ajouter.
        self._create_and_validate_achat(unit_price='9999')
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        data = res.data.get('results', res.data)[0]
        self.assertEqual(data['montant_consomme'], 300.0)
        self.assertEqual(data['montant_restant'], 700.0)
        self.assertEqual(data['pourcentage_consomme'], 30.0)

    def test_threshold_reached_blocks_new_achat_creation(self):
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_execute_achat(unit_price='900')  # 90% consommé (exécuté)
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_below_threshold_allows_achat_creation(self):
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_execute_achat(unit_price='300')  # 30% consommé (exécuté)
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_ral_cannot_unblock_budget(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{budget.id}/unblock/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dg_unblock_allows_creation_despite_threshold(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_execute_achat(unit_price='900')  # 90% consommé — bloqué

        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{budget.id}/unblock/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_increasing_budget_lifts_block(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_execute_achat(unit_price='900')  # 90% consommé — bloqué

        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{budget.id}/', {'montant_annuel': '10000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_dg_not_notified_on_validation_only(self):
        from apps.notifications.models import Notification
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_validate_achat(unit_price='900')  # validée seulement — pas de notif
        self.assertEqual(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_ral_seuil').count(), 0
        )

    def test_dg_notified_once_when_threshold_reached_on_execution(self):
        from apps.notifications.models import Notification
        RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self._create_and_execute_achat(unit_price='900')  # exécutée → franchit 85% → notifie
        self.assertEqual(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_ral_seuil').count(), 1
        )
        # Débloque pour permettre une seconde exécution, sans redéclencher la notif
        budget = RALBudget.objects.get(year=self.year)
        budget.is_manually_unblocked = True
        budget.save(update_fields=['is_manually_unblocked'])
        self._create_and_execute_achat(unit_price='10')
        self.assertEqual(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_ral_seuil').count(), 1
        )

    # ── Évolution 4 : budget obligatoire ──────────────────────────────────
    def test_creation_blocked_when_no_budget_exists_at_all(self):
        # Aucun RALBudget créé pour self.year (contrairement à un budget
        # simplement épuisé, testé plus haut) — la simple ABSENCE de budget
        # doit aussi bloquer, ce qui était le trou comblé par l'Évolution 4.
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('budget', res.data['detail'].lower())

    def test_creation_links_budget_when_available(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        req = UnifiedRequest.objects.get(id=res.data['id'])
        self.assertEqual(req.budget_id, budget.id)

    def test_client_supplied_budget_is_ignored(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        other_year_budget = RALBudget.objects.create(
            year=self.year - 1, montant_annuel=Decimal('500'), created_by=self.dg
        )
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only', 'budget': other_year_budget.id,
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        req = UnifiedRequest.objects.get(id=res.data['id'])
        self.assertEqual(req.budget_id, budget.id)  # jamais celui envoyé par le client

    def test_update_to_achat_type_reenforces_budget_check(self):
        # Contourne l'obligation de budget en créant en 'entree' (aucun
        # budget requis) puis en modifiant le type vers 'achat' — sans
        # budget défini pour self.year, ceci doit rester bloqué.
        req = UnifiedRequest.objects.create(request_type='entree', requested_by=self.stock, status='brouillon')
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'/api/requests/{req.id}/', {'request_type': 'achat'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertIsNone(req.budget_id)

    def test_update_to_achat_type_links_budget_when_available(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        req = UnifiedRequest.objects.create(request_type='entree', requested_by=self.stock, status='brouillon')
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'/api/requests/{req.id}/', {'request_type': 'achat'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.budget_id, budget.id)

    def test_update_away_from_achat_clears_budget_link(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='brouillon', budget=budget,
        )
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'/api/requests/{req.id}/', {'request_type': 'entree'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertIsNone(req.budget_id)

    def test_budget_deletion_blocked_when_referenced_by_requests(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='brouillon', budget=budget,
        )
        self.client.force_authenticate(self.dg)
        res = self.client.delete(f'{self.url}{budget.id}/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(RALBudget.objects.filter(id=budget.id).exists())

    def test_budget_deletion_allowed_when_unreferenced(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self.client.force_authenticate(self.dg)
        res = self.client.delete(f'{self.url}{budget.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_blocked_creation_logs_audit_denied_without_notification(self):
        from apps.accounts.models import AuditLog
        from apps.notifications.models import Notification
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.ACTION_DENIED, model_name='UnifiedRequest').exists()
        )
        self.assertEqual(Notification.objects.filter(recipient=self.dg).count(), 0)

    # ── Cohérence historique du rattachement (correction demandée par le DG) ─
    # Le lien `budget` doit être une photographie figée de l'année de
    # CRÉATION de la demande : ni une édition ultérieure de la demande, ni
    # la création d'un budget pour une autre année, ni une modification du
    # montant annuel d'un budget déjà lié, ne doivent jamais le faire changer.
    def test_edit_never_reassigns_budget_after_later_year_budget_created(self):
        budget_2026 = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/requests/', {
            'request_type': 'achat', 'validation_type': 'dg_only',
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '10'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        req = UnifiedRequest.objects.get(id=res.data['id'])
        self.assertEqual(req.budget_id, budget_2026.id)

        # Un budget est créé pour l'année suivante — ne doit avoir aucun effet
        # rétroactif sur une demande déjà rattachée au budget de son année de
        # création.
        RALBudget.objects.create(year=self.year + 1, montant_annuel=Decimal('2000'), created_by=self.dg)

        res = self.client.patch(
            f'/api/requests/{req.id}/', {'motif': 'motif modifié après création du budget suivant'}, format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.budget_id, budget_2026.id)

    def test_updating_budget_amount_does_not_reassign_existing_request(self):
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='brouillon', budget=budget,
        )
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{budget.id}/', {'montant_annuel': '5000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.budget_id, budget.id)
        self.assertEqual(req.budget.montant_annuel, Decimal('5000'))

    def test_montant_annuel_change_creates_structured_audit_log(self):
        """Évolution 8 — traçabilité avant/après sur RALBudget.montant_annuel
        (voir gertrack.business_rules.AUDIT_TRACKED_FIELDS)."""
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{budget.id}/', {'montant_annuel': '2000000'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        log = AuditLog.objects.get(model_name='RALBudget', object_id=str(budget.id), field_name='montant_annuel')
        self.assertEqual(log.old_value, {'montant_annuel': 1000000.0})
        self.assertEqual(log.new_value, {'montant_annuel': 2000000.0})

    def test_is_urgent_change_creates_structured_audit_log(self):
        """Évolution 8 — traçabilité avant/après sur UnifiedRequest.is_urgent
        (voir gertrack.business_rules.AUDIT_TRACKED_FIELDS)."""
        budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        project = Project.objects.create(code='PRJ-URG', name='Projet Urgence', created_by=self.dg)
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='brouillon',
            validation_type='dg_only', budget=budget, project=project, is_urgent=False,
        )
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'/api/requests/{req.id}/', {'is_urgent': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        log = AuditLog.objects.get(model_name='UnifiedRequest', object_id=str(req.id), field_name='is_urgent')
        self.assertEqual(log.old_value, {'is_urgent': False})
        self.assertEqual(log.new_value, {'is_urgent': True})

    def test_no_is_urgent_change_creates_no_structured_log(self):
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.stock, status='brouillon', is_urgent=False,
        )
        self.client.force_authenticate(self.stock)
        res = self.client.patch(f'/api/requests/{req.id}/', {'motif': 'juste un motif'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertFalse(
            AuditLog.objects.filter(model_name='UnifiedRequest', object_id=str(req.id), field_name='is_urgent').exists()
        )


class SupplierPerformanceTests(APITestCase):
    """Phase F — indicateur de performance fournisseur (§7)."""

    def setUp(self):
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.supplier = Supplier.objects.create(name='Fournisseur Perf')
        self.product = Product.objects.create(
            code='PRD-PERF', designation='Produit perf', unit='pcs',
            stock_actuel=Decimal('0'), stock_securite=Decimal('0'),
        )

    def _closed_order(self, prevue, reelle):
        from .models import RequestItem
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, status='executee',
            supplier=self.supplier, logistics_status='cloturee',
            date_livraison_prevue=prevue, date_livraison_reelle=reelle,
        )
        RequestItem.objects.create(request=req, product=self.product, quantity=Decimal('1'))
        return req

    def test_performance_stats_computed_from_closed_orders(self):
        import datetime
        d = datetime.date(2026, 1, 10)
        self._closed_order(d, d)                              # à temps
        self._closed_order(d, d + datetime.timedelta(days=3))  # en retard de 3j

        self.assertEqual(self.supplier.taux_livraison_a_temps, 50.0)
        self.assertEqual(self.supplier.delai_moyen_jours, 1.5)


class BudgetDepassementNotificationTests(APITestCase):
    """
    Régression / couverture : aucune vérification automatisée n'existait
    pour la détection de dépassement budgétaire (submit() déclenche
    notify_budget_depasse si le montant de la demande dépasse le budget
    restant du projet lié).
    """

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.pm    = User.objects.create_user(username='pm', password='pass', role=User.ROLE_PM)
        self.project = Project.objects.create(
            code='PRJ-BUDGET', name='Projet Budget', project_manager=self.pm,
            budget=Decimal('1000'),
        )
        self.product = Product.objects.create(
            code='PRD-BUDGET', designation='Produit budget', unit='pcs',
            stock_actuel=Decimal('100'), stock_securite=Decimal('5'),
        )

    def _submit_achat(self, unit_price, quantity='1'):
        from .models import RequestItem
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock,
            validation_type='dg_only', project=self.project,
        )
        RequestItem.objects.create(
            request=req, product=self.product,
            quantity=Decimal(quantity), unit_price=Decimal(unit_price),
        )
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'/api/requests/{req.id}/submit/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        return req

    def test_submit_over_budget_notifies_dg(self):
        from apps.notifications.models import Notification
        req = self._submit_achat(unit_price='2000')  # dépasse le budget de 1000
        self.assertTrue(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_depasse', object_id=self.project.id).exists()
        )

    def test_submit_within_budget_does_not_notify(self):
        from apps.notifications.models import Notification
        self._submit_achat(unit_price='100')  # bien en dessous du budget de 1000
        self.assertFalse(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_depasse').exists()
        )


class UrgentPurchaseRequestTests(APITestCase):
    """
    Évolution 5 — demandes d'achat urgentes : réservées à Chef de Projet /
    Magasinier / RAL, obligatoirement liées à un projet, notifiées
    simultanément au DOP et au DG à la soumission. Le premier des deux à
    statuer (valider OU refuser) décide seul — l'action de l'autre devient
    caduque (voir UnifiedRequest._act_on_urgent).
    """

    url = '/api/requests/'

    def setUp(self):
        self.dg        = User.objects.create_user(username='dg_urg', password='pass', role=User.ROLE_DG)
        self.dop       = User.objects.create_user(username='dop_urg', password='pass', role=User.ROLE_OPS_CHIEF)
        self.stock     = User.objects.create_user(username='stock_urg', password='pass', role=User.ROLE_STOCK)
        self.pm        = User.objects.create_user(username='pm_urg', password='pass', role=User.ROLE_PM)
        self.mag       = User.objects.create_user(username='mag_urg', password='pass', role=User.ROLE_MAGASINIER)
        self.financier = User.objects.create_user(username='financier_urg', password='pass', role=User.ROLE_FINANCIAL)
        self.project = Project.objects.create(
            code='PRJ-URG', name='Projet Urgent', project_manager=self.pm, budget=Decimal('1000000'),
        )
        self.product = Product.objects.create(
            code='PRD-URG', designation='Produit urgent', unit='pcs',
            stock_actuel=Decimal('50'), stock_securite=Decimal('5'),
        )

    def _create_urgent(self, user, project_id, quantity='1', unit_price='100'):
        self.client.force_authenticate(user)
        return self.client.post(self.url, {
            'request_type': 'achat', 'is_urgent': True, 'project': project_id,
            'items': [{'product': self.product.id, 'quantity': quantity, 'unit_price': unit_price}],
        }, format='json')

    def _submit(self, user, req_id):
        self.client.force_authenticate(user)
        return self.client.post(f'{self.url}{req_id}/submit/')

    # ── Création : rôles autorisés et obligation de projet ───────────────────
    def test_pm_can_create_urgent_achat_for_own_project(self):
        res = self._create_urgent(self.pm, self.project.id)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['validation_type'], 'urgent_dop_ou_dg')

    def test_magasinier_can_create_urgent_achat(self):
        res = self._create_urgent(self.mag, self.project.id)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_ral_can_create_urgent_achat(self):
        RALBudget.objects.create(year=timezone.now().year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        res = self._create_urgent(self.stock, self.project.id)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_dop_cannot_create_urgent_achat(self):
        res = self._create_urgent(self.dop, self.project.id)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_urgent_achat_requires_project(self):
        self.client.force_authenticate(self.mag)
        res = self.client.post(self.url, {
            'request_type': 'achat', 'is_urgent': True,
            'items': [{'product': self.product.id, 'quantity': '1', 'unit_price': '100'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_is_urgent_rejected_for_non_achat_type(self):
        self.client.force_authenticate(self.mag)
        res = self.client.post(self.url, {
            'request_type': 'entree', 'is_urgent': True, 'project': self.project.id,
            'items': [{'product': self.product.id, 'quantity': '1'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Budget : projet pour PM/Magasinier, budget annuel RAL pour le RAL ────
    def test_urgent_pm_achat_not_tied_to_ral_budget(self):
        # Aucun RALBudget n'existe pour l'année en cours — ne doit PAS bloquer
        # une urgente du Chef de Projet, financée par le projet et non par le
        # budget annuel RAL (RALBudget.montant_consomme ne compte de toute
        # façon que les demandes dont l'auteur a le rôle RAL).
        res = self._create_urgent(self.pm, self.project.id)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        req = UnifiedRequest.objects.get(id=res.data['id'])
        self.assertIsNone(req.budget_id)

    def test_urgent_ral_achat_still_requires_ral_budget(self):
        # Contrairement au Chef de Projet/Magasinier, une urgente du RAL
        # reste soumise à l'obligation de budget annuel RAL (Évolution 4).
        res = self._create_urgent(self.stock, self.project.id)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── Notification simultanée DOP + DG ──────────────────────────────────
    def test_submission_notifies_dop_and_dg_simultaneously(self):
        from apps.notifications.models import Notification
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)
        self.assertTrue(
            Notification.objects.filter(recipient=self.dop, notif_type='demande_soumise', object_id=req_id).exists()
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.dg, notif_type='demande_soumise', object_id=req_id).exists()
        )

    # ── Course : le premier qui valide gagne ──────────────────────────────
    def test_dop_validates_first_wins(self):
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        req = UnifiedRequest.objects.get(id=req_id)
        self.assertEqual(req.status, 'validee')
        self.assertEqual(req.dop_validated_by_id, self.dop.id)
        self.assertIsNone(req.dg_validated_by_id)

    def test_dg_second_validation_attempt_becomes_moot(self):
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/validate-dg/', {'comment': 'trop tard'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        req = UnifiedRequest.objects.get(id=req_id)
        self.assertEqual(req.status, 'validee')  # inchangé, toujours DOP
        self.assertIsNone(req.dg_validated_by_id)

    def test_dg_validates_first_wins(self):
        res = self._create_urgent(self.mag, self.project.id)
        req_id = res.data['id']
        self._submit(self.mag, req_id)

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        req = UnifiedRequest.objects.get(id=req_id)
        self.assertEqual(req.status, 'validee')
        self.assertEqual(req.dg_validated_by_id, self.dg.id)
        self.assertIsNone(req.dop_validated_by_id)

    # ── Symétrie : le refus fait aussi la course ──────────────────────────
    def test_dop_rejects_first_dg_validation_becomes_moot(self):
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{req_id}/reject-dop/', {'comment': 'non prioritaire'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/validate-dg/', {'comment': 'trop tard'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        req = UnifiedRequest.objects.get(id=req_id)
        self.assertEqual(req.status, 'refusee')

    def test_dg_rejects_first_dop_rejection_becomes_moot(self):
        res = self._create_urgent(self.mag, self.project.id)
        req_id = res.data['id']
        self._submit(self.mag, req_id)

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/reject-dg/', {'comment': 'budget insuffisant'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{req_id}/reject-dop/', {'comment': 'trop tard'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Pas de substitution RAL sur la course urgente ─────────────────────
    # Contrairement au circuit habituel (où le RAL peut se substituer au DOP
    # pour les demandes de magasinier/chef de projet — voir
    # UnifiedRequestViewSet.validate_dop), la course urgente est strictement
    # réservée aux rôles réels DOP et DG.
    def test_ral_cannot_substitute_for_dop_on_urgent(self):
        RALBudget.objects.create(year=timezone.now().year, montant_annuel=Decimal('1000000'), created_by=self.dg)
        res = self._create_urgent(self.mag, self.project.id)
        req_id = res.data['id']
        self._submit(self.mag, req_id)

        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── Traçabilité de la tentative caduque ───────────────────────────────
    def test_second_actor_attempt_logged_as_denied_without_notification(self):
        from apps.accounts.models import AuditLog
        from apps.notifications.models import Notification
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')

        before = Notification.objects.filter(recipient=self.dg).count()
        self.client.force_authenticate(self.dg)
        self.client.post(f'{self.url}{req_id}/validate-dg/', {'comment': 'trop tard'}, format='json')
        after = Notification.objects.filter(recipient=self.dg).count()

        self.assertEqual(before, after)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_DENIED, model_name='UnifiedRequest', object_id=str(req_id)
            ).exists()
        )

    # ── Audit du circuit urgent (post-validation = variante, pas un second
    # workflow) : le PDF doit rester généralisable même quand seul le DOP a
    # validé — dg_validated_by/dg_validated_at restent None, contrairement à
    # toute demande passée par le circuit classique dg_only/dop_then_dg où
    # le DG valide toujours en dernier.
    def test_pdf_generation_for_dop_only_validated_urgent_achat(self):
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        req = UnifiedRequest.objects.get(id=req_id)
        self.assertIsNone(req.dg_validated_by_id)  # confirme le cas limite testé

        self.client.force_authenticate(self.dg)
        res = self.client.get(f'{self.url}{req_id}/pdf/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content[:200])
        self.assertEqual(res['Content-Type'], 'application/pdf')

    # ── Statistiques : une urgente ne doit jamais disparaître parce qu'elle
    # porte is_urgent=True — elle reste `request_type='achat'` comme toute
    # autre, donc comptée par tout ce qui filtre déjà sur ce champ.
    def test_urgent_achat_counted_in_global_stats(self):
        res = self._create_urgent(self.pm, self.project.id)
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')

        self.client.force_authenticate(self.dg)
        res = self.client.get(f'{self.url}stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res.data['achat'], 1)
        self.assertGreaterEqual(res.data['validee'], 1)

    def test_urgent_achat_counted_in_project_budget_consomme(self):
        res = self._create_urgent(self.pm, self.project.id, unit_price='200')
        req_id = res.data['id']
        self._submit(self.pm, req_id)

        self.client.force_authenticate(self.dop)
        self.client.post(f'{self.url}{req_id}/validate-dop/', {'comment': 'ok'}, format='json')

        # Évolution 7 : le budget projet n'est consommé qu'à l'exécution
        # financière, jamais à la simple validation — le circuit logistique
        # ne peut d'ailleurs pas démarrer avant cette étape.
        self.client.force_authenticate(self.financier)
        res = self.client.post(f'{self.url}{req_id}/execute-financial/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        self.client.force_authenticate(self.pm)
        res = self.client.post(
            f'{self.url}{req_id}/advance-logistics/',
            {'logistics_status': 'reception_magasin'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        self.project.refresh_from_db()
        self.assertEqual(self.project.budget_consomme, 200.0)


class FinancialExecutionTests(APITestCase):
    """
    Évolution 7 — Responsable Financier : la validation n'entraîne plus
    directement l'exécution d'une demande d'achat. Seul ce rôle peut
    l'exécuter (POST /execute-financial/), et c'est uniquement à ce
    moment-là que le budget (RAL et projet) est réellement consommé —
    jamais à la simple validation. La réception magasin (circuit
    logistique) reste un événement séparé et indépendant, qui ne démarre
    qu'après cette exécution.
    """

    url = '/api/requests/'

    def setUp(self):
        self.dg        = User.objects.create_user(username='dg_fin', password='pass', role=User.ROLE_DG)
        self.stock     = User.objects.create_user(username='stock_fin', password='pass', role=User.ROLE_STOCK)
        self.financier = User.objects.create_user(username='financier_fin', password='pass', role=User.ROLE_FINANCIAL)
        self.pm        = User.objects.create_user(username='pm_fin', password='pass', role=User.ROLE_PM)
        self.product = Product.objects.create(
            code='PRD-FIN', designation='Produit financier', unit='pcs',
            stock_actuel=Decimal('50'), stock_securite=Decimal('5'),
        )
        self.project = Project.objects.create(
            code='PRJ-FIN', name='Projet Financier', project_manager=self.pm, budget=Decimal('1000'),
        )
        self.year = timezone.now().year
        self.ral_budget = RALBudget.objects.create(year=self.year, montant_annuel=Decimal('1000'), created_by=self.dg)

    def _create_and_validate_achat(self, unit_price, quantity='1', project=None):
        req = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.stock, validation_type='dg_only', project=project,
        )
        RequestItem.objects.create(
            request=req, product=self.product, quantity=Decimal(quantity), unit_price=Decimal(unit_price),
        )
        self.client.force_authenticate(self.stock)
        res = self.client.post(f'{self.url}{req.id}/submit/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req.id}/validate-dg/', {'comment': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'validee')
        return req

    # ── Validation ≠ exécution ──────────────────────────────────────────────
    def test_validation_does_not_set_executee(self):
        req = self._create_and_validate_achat('900')
        self.assertEqual(req.status, 'validee')
        self.assertIsNone(req.financial_execution_by)

    def test_validation_does_not_consume_ral_budget(self):
        self._create_and_validate_achat('900')
        self.ral_budget.refresh_from_db()
        self.assertEqual(self.ral_budget.montant_consomme, 0.0)

    def test_validation_does_not_consume_project_budget(self):
        self._create_and_validate_achat('900', project=self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.budget_consomme, 0.0)

    # ── Exécution financière ─────────────────────────────────────────────────
    def test_financial_officer_can_execute(self):
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        res = self.client.post(f'{self.url}{req.id}/execute-financial/', {'notes': 'ok'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'executee')
        self.assertEqual(req.financial_execution_by_id, self.financier.id)
        self.assertIsNotNone(req.financial_execution_at)
        self.assertEqual(req.financial_execution_notes, 'ok')

    def test_execution_consumes_ral_budget(self):
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.ral_budget.refresh_from_db()
        self.assertEqual(self.ral_budget.montant_consomme, 900.0)

    def test_execution_consumes_project_budget(self):
        req = self._create_and_validate_achat('900', project=self.project)
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.project.refresh_from_db()
        self.assertEqual(self.project.budget_consomme, 900.0)

    def test_execution_does_not_create_stock_movement(self):
        """L'exécution financière ne doit jamais se substituer à la
        réception magasin — aucun mouvement de stock avant elle."""
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertFalse(StockMovement.objects.filter(origin_ref=req.reference).exists())

    def test_execution_does_not_touch_logistics_status(self):
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        req.refresh_from_db()
        self.assertEqual(req.logistics_status, '')

    def test_non_financial_officer_with_visibility_cannot_execute(self):
        req = self._create_and_validate_achat('900')
        for user in [self.dg, self.stock]:
            self.client.force_authenticate(user)
            res = self.client.post(f'{self.url}{req.id}/execute-financial/')
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_pm_cannot_even_see_request_to_execute(self):
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.pm)
        res = self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_financial_officer_cannot_execute_non_achat_request(self):
        # Invisible dans son périmètre (get_queryset scope 'achat' + 'validee'
        # uniquement) : 404, pas 403 — même résultat pratique.
        UnifiedRequest.objects.create(request_type='entree', requested_by=self.stock, status='validee')
        self.client.force_authenticate(self.financier)
        other_id = UnifiedRequest.objects.filter(request_type='entree').first().id
        res = self.client.post(f'{self.url}{other_id}/execute-financial/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_financial_officer_cannot_execute_unvalidated_achat(self):
        req = UnifiedRequest.objects.create(request_type='achat', requested_by=self.stock, status='brouillon')
        self.client.force_authenticate(self.financier)
        res = self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ── Idempotence (point 7) ────────────────────────────────────────────────
    def test_concurrent_double_execution_denied_at_model_level(self):
        """Protection contre un vrai appel concurrent (deux requêtes quasi
        simultanées passant toutes les deux le filtre get_queryset avant que
        l'une des deux n'ait validé) : select_for_update + transaction
        atomique garantissent qu'une seule aboutit, l'autre lève
        DuplicateExecutionError — vérifié ici directement au niveau modèle,
        le point réellement protégé par le verrou de ligne."""
        req = self._create_and_validate_achat('900')
        req.execute_financial(self.financier, 'premier appel')
        req.refresh_from_db()
        with self.assertRaises(DuplicateExecutionError):
            req.execute_financial(self.financier, 'second appel')

    def test_sequential_repeat_call_after_execution_returns_not_found(self):
        """Une fois exécutée, la demande disparaît immédiatement de la liste
        du Financier (exigence explicite du workflow) — un second appel API
        séquentiel (retry réseau, double-clic déjà traité côté serveur) ne
        peut donc plus jamais l'atteindre."""
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        res1 = self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        res2 = self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertEqual(res2.status_code, status.HTTP_404_NOT_FOUND)

    # ── Audit ────────────────────────────────────────────────────────────────
    def test_execution_logged_with_action_execute(self):
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_EXECUTE, model_name='UnifiedRequest', object_id=str(req.id)
            ).exists()
        )

    # ── Visibilité (Financier) ───────────────────────────────────────────────
    def test_financial_officer_sees_only_validated_achats(self):
        validated = self._create_and_validate_achat('100')
        brouillon = UnifiedRequest.objects.create(request_type='achat', requested_by=self.stock, status='brouillon')
        entree    = UnifiedRequest.objects.create(request_type='entree', requested_by=self.stock, status='validee')

        self.client.force_authenticate(self.financier)
        res = self.client.get(self.url)
        ids = [r['id'] for r in res.data.get('results', res.data)]
        self.assertIn(validated.id, ids)
        self.assertNotIn(brouillon.id, ids)
        self.assertNotIn(entree.id, ids)

    def test_request_disappears_from_financial_officer_list_after_execution(self):
        req = self._create_and_validate_achat('100')
        self.client.force_authenticate(self.financier)
        res = self.client.get(self.url)
        self.assertIn(req.id, [r['id'] for r in res.data.get('results', res.data)])

        self.client.post(f'{self.url}{req.id}/execute-financial/')

        res = self.client.get(self.url)
        self.assertNotIn(req.id, [r['id'] for r in res.data.get('results', res.data)])

    def test_financial_officer_can_view_pdf_of_validated_achat(self):
        req = self._create_and_validate_achat('900')
        self.client.force_authenticate(self.financier)
        res = self.client.get(f'{self.url}{req.id}/pdf-preview/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_financial_officer_cannot_create_request(self):
        self.client.force_authenticate(self.financier)
        res = self.client.post(self.url, {
            'request_type': 'entree',
            'items': [{'product': self.product.id, 'quantity': '1'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── Notifications (séquence exacte demandée) ────────────────────────────
    def test_validation_notifies_financial_officer(self):
        req = self._create_and_validate_achat('100')
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.financier, notif_type='a_executer_financier', object_id=req.id
            ).exists()
        )

    def test_execution_notifies_requester_and_ral(self):
        req = self._create_and_validate_achat('100')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.stock, notif_type='demande_executee_financiere', object_id=req.id
            ).exists()
        )

    def test_ral_budget_threshold_notified_at_execution_not_validation(self):
        req = self._create_and_validate_achat('900')  # 90% si exécuté
        self.assertEqual(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_ral_seuil').count(), 0
        )
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        self.assertEqual(
            Notification.objects.filter(recipient=self.dg, notif_type='budget_ral_seuil').count(), 1
        )

    def test_project_block_triggered_at_execution_not_validation(self):
        WeeklyReport.objects.create(
            project=self.project, week_number=1, year=self.year, report_date=timezone.now().date(),
            global_progress_snapshot=Decimal('20'), planned_progress=Decimal('50'),
        )
        req = self._create_and_validate_achat('900', project=self.project)  # 90% si exécuté, projet en retard
        self.project.refresh_from_db()
        self.assertFalse(self.project.is_budget_blocked)  # validée seulement, pas encore bloqué

        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')

        self.project.refresh_from_db()
        self.assertTrue(self.project.is_budget_blocked)

    # ── Circuit logistique : démarre seulement après exécution ─────────────
    def test_logistics_blocked_before_execution(self):
        req = self._create_and_validate_achat('100')
        self.client.force_authenticate(self.stock)
        res = self.client.post(
            f'{self.url}{req.id}/advance-logistics/',
            {'logistics_status': 'commande_envoyee'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logistics_allowed_after_execution(self):
        req = self._create_and_validate_achat('100')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')

        self.client.force_authenticate(self.stock)
        res = self.client.post(
            f'{self.url}{req.id}/advance-logistics/',
            {'logistics_status': 'commande_envoyee'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    def test_reception_after_execution_creates_stock_movement(self):
        req = self._create_and_validate_achat('100')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')

        self.client.force_authenticate(self.stock)
        res = self.client.post(
            f'{self.url}{req.id}/advance-logistics/',
            {'logistics_status': 'reception_magasin'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'executee')
        self.assertTrue(StockMovement.objects.filter(origin_ref=req.reference).exists())

    def test_reception_does_not_reset_financial_execution_info(self):
        req = self._create_and_validate_achat('100')
        self.client.force_authenticate(self.financier)
        self.client.post(f'{self.url}{req.id}/execute-financial/')
        req.refresh_from_db()
        exec_by, exec_at = req.financial_execution_by_id, req.financial_execution_at

        self.client.force_authenticate(self.stock)
        self.client.post(
            f'{self.url}{req.id}/advance-logistics/',
            {'logistics_status': 'reception_magasin'}, format='json',
        )
        req.refresh_from_db()
        self.assertEqual(req.financial_execution_by_id, exec_by)
        self.assertEqual(req.financial_execution_at, exec_at)


class UnifiedRequestReferenceGenerationTests(APITestCase):
    """
    _generate_reference() calculait auparavant count()+1 : dès qu'un écart
    existe entre le nombre de lignes et le plus grand suffixe déjà attribué
    (ligne supprimée, données non séquentielles), le numéro recalculé entre
    en collision avec une référence existante et casse la contrainte unique
    en base — reproduit en pratique avec deux "ES-2026-000X" identiques.
    """

    def setUp(self):
        self.stock = User.objects.create_user(
            username='stock_ref', password='pass', role=User.ROLE_STOCK,
        )

    def test_two_requests_of_same_type_get_distinct_references(self):
        r1 = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.stock, validation_type='dg_only',
        )
        r2 = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.stock, validation_type='dg_only',
        )
        self.assertNotEqual(r1.reference, r2.reference)

    def test_reference_survives_gap_in_existing_numbers(self):
        # Simule un écart : une ligne existante porte déjà un numéro plus
        # élevé que ne le suggère le simple décompte des lignes du type.
        r1 = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.stock, validation_type='dg_only',
        )
        year = r1.reference.split('-')[1]
        r1.reference = f'BS-{year}-0007'
        r1.save()

        r2 = UnifiedRequest.objects.create(
            request_type='sortie', requested_by=self.stock, validation_type='dg_only',
        )
        self.assertEqual(r2.reference, f'BS-{year}-0008')
