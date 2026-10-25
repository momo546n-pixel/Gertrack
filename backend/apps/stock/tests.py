from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, User
from apps.products.models import Product

from .models import StockMovement, Warehouse


class StockMovementReadOnlyTests(APITestCase):
    """
    Le module "Mouvements" ne doit plus permettre de créer un mouvement de
    stock directement : seule la validation d'une demande (UnifiedRequest)
    peut le faire, via le modèle. L'API REST reste accessible en lecture
    seule (historique, dashboard, alertes).
    """

    def setUp(self):
        self.stock_manager = User.objects.create_user(
            username='stock', password='pass', role=User.ROLE_STOCK,
        )
        self.product = Product.objects.create(
            code='PRD-1', designation='Produit test', unit='pcs',
            stock_actuel=Decimal('50'), stock_securite=Decimal('5'),
        )
        self.warehouse = Warehouse.objects.create(code='WH1', name='Magasin Principal')

    def test_cannot_create_movement_via_api(self):
        self.client.force_authenticate(self.stock_manager)
        payload = {
            'product': self.product.id,
            'movement_type': StockMovement.ENTRY,
            'quantity': '10',
            'date': '2026-01-01',
        }
        res = self.client.post('/api/stock/movements/', payload, format='json')
        self.assertIn(res.status_code, (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND))

    def test_movements_list_still_readable(self):
        StockMovement.objects.create(
            product=self.product, movement_type=StockMovement.ENTRY,
            quantity=Decimal('10'), stock_before=Decimal('50'), stock_after=Decimal('60'),
            date='2026-01-01', created_by=self.stock_manager,
        )
        self.client.force_authenticate(self.stock_manager)
        res = self.client.get('/api/stock/movements/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movement_created_internally_by_request_validation_still_works(self):
        """
        La création interne via le modèle (utilisée par
        UnifiedRequest._execute_stock_movements) n'est pas affectée par le
        passage de la vue en lecture seule.
        """
        movement = StockMovement.objects.create(
            product=self.product, movement_type=StockMovement.ENTRY,
            quantity=Decimal('10'), stock_before=Decimal('50'), stock_after=Decimal('60'),
            date='2026-01-01', created_by=self.stock_manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actuel, Decimal('60'))
        self.assertIsNotNone(movement.pk)


class WarehouseHardDeleteTests(APITestCase):
    """
    "Supprimer" (delete-permanently) doit supprimer définitivement le magasin
    ET le compte magasinier titulaire — contrairement à destroy() qui ne fait
    que désactiver (is_active=False, réversible).
    """

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.magasinier = User.objects.create_user(
            username='mag1', password='pass', role=User.ROLE_MAGASINIER,
        )
        self.warehouse = Warehouse.objects.create(
            code='WH-DEL', name='À supprimer', manager=self.magasinier,
        )

    def test_dg_can_hard_delete_warehouse_and_account(self):
        self.client.force_authenticate(self.dg)
        res = self.client.delete(f'/api/stock/warehouses/{self.warehouse.id}/delete-permanently/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Warehouse.objects.filter(id=self.warehouse.id).exists())
        self.assertFalse(User.objects.filter(id=self.magasinier.id).exists())

    def test_non_dg_cannot_hard_delete(self):
        self.client.force_authenticate(self.stock)
        res = self.client.delete(f'/api/stock/warehouses/{self.warehouse.id}/delete-permanently/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Warehouse.objects.filter(id=self.warehouse.id).exists())

    def test_historical_requests_survive_account_hard_delete(self):
        """
        Traçabilité : l'historique des demandes du magasinier doit survivre
        à la suppression de son compte (requested_by passe à null au lieu
        de supprimer les demandes en cascade).
        """
        from apps.requests.models import UnifiedRequest
        req = UnifiedRequest.objects.create(
            request_type='entree', requested_by=self.magasinier, warehouse=self.warehouse,
        )
        self.client.force_authenticate(self.dg)
        res = self.client.delete(f'/api/stock/warehouses/{self.warehouse.id}/delete-permanently/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        req.refresh_from_db()
        self.assertIsNone(req.requested_by)


class WarehouseManagerAuditTrailTests(APITestCase):
    """
    Évolution 8 — traçabilité avant/après sur le gérant d'un magasin.

    Découverte en écrivant ces tests : contrairement à l'hypothèse initiale
    ("Warehouse.manager est fixé une fois pour toutes, jamais réassigné"),
    WarehouseSerializer expose `manager` en champ écrivable standard (pas
    read_only) — un DG peut donc réaffecter directement le FK via un PATCH
    générique, en plus du flux prévu (changement d'identifiant du même
    gérant via `mag_username`). Les deux transitions sont réellement
    possibles et sont donc toutes les deux tracées (voir
    gertrack.business_rules.AUDIT_TRACKED_FIELDS) — revoir si cette
    réaffectation générique devrait être interdite reste une question de
    permissions hors périmètre de cette évolution (traçabilité uniquement).
    """

    def setUp(self):
        self.dg = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.magasinier = User.objects.create_user(
            username='mag_old', password='pass', role=User.ROLE_MAGASINIER,
        )
        self.warehouse = Warehouse.objects.create(
            code='WH-AUDIT', name='Magasin Audit', manager=self.magasinier,
        )

    def test_manager_username_change_creates_structured_audit_log(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'/api/stock/warehouses/{self.warehouse.id}/', {
            'mag_username': 'mag_new',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        log = AuditLog.objects.get(model_name='Warehouse', object_id=str(self.warehouse.id), field_name='manager_username')
        self.assertEqual(log.old_value, {'manager_username': 'mag_old'})
        self.assertEqual(log.new_value, {'manager_username': 'mag_new'})

    def test_manager_reassignment_via_generic_patch_is_tracked(self):
        other = User.objects.create_user(
            username='mag_other', password='pass', role=User.ROLE_MAGASINIER,
            first_name='Autre', last_name='Gérant',
        )
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'/api/stock/warehouses/{self.warehouse.id}/', {
            'manager': other.id,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.warehouse.refresh_from_db()
        self.assertEqual(self.warehouse.manager_id, other.id)

        log = AuditLog.objects.get(model_name='Warehouse', object_id=str(self.warehouse.id), field_name='manager')
        self.assertEqual(log.old_value, {'manager': 'mag_old'})
        self.assertEqual(log.new_value, {'manager': 'Autre Gérant'})

    def test_no_username_change_creates_no_structured_log(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'/api/stock/warehouses/{self.warehouse.id}/', {
            'mag_phone': '221999999',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertFalse(
            AuditLog.objects.filter(model_name='Warehouse', object_id=str(self.warehouse.id), field_name='manager_username').exists()
        )


class StockMovementQuantityValidationTests(APITestCase):
    """
    Régression : seul l'ajustement rejetait une quantité négative — une
    entrée ou une sortie à quantité négative/nulle passait silencieusement
    (une sortie négative augmentait même le stock au lieu de le diminuer,
    contournant le contrôle de stock insuffisant).
    """

    def setUp(self):
        self.product = Product.objects.create(
            code='PRD-QTY', designation='Produit test quantité', unit='pcs',
            stock_actuel=Decimal('50'), stock_securite=Decimal('5'),
        )

    def test_entry_rejects_negative_quantity(self):
        with self.assertRaises(ValueError):
            StockMovement.objects.create(
                product=self.product, movement_type=StockMovement.ENTRY,
                quantity=Decimal('-10'), date='2026-01-01',
            )

    def test_entry_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            StockMovement.objects.create(
                product=self.product, movement_type=StockMovement.ENTRY,
                quantity=Decimal('0'), date='2026-01-01',
            )

    def test_exit_rejects_negative_quantity(self):
        with self.assertRaises(ValueError):
            StockMovement.objects.create(
                product=self.product, movement_type=StockMovement.EXIT,
                quantity=Decimal('-10'), date='2026-01-01',
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actuel, Decimal('50'))

    def test_exit_rejects_insufficient_stock(self):
        with self.assertRaises(ValueError):
            StockMovement.objects.create(
                product=self.product, movement_type=StockMovement.EXIT,
                quantity=Decimal('1000'), date='2026-01-01',
            )

    def test_valid_entry_and_exit_update_stock_correctly(self):
        StockMovement.objects.create(
            product=self.product, movement_type=StockMovement.ENTRY,
            quantity=Decimal('20'), date='2026-01-01',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actuel, Decimal('70'))

        StockMovement.objects.create(
            product=self.product, movement_type=StockMovement.EXIT,
            quantity=Decimal('30'), date='2026-01-01',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actuel, Decimal('40'))


class StockMovementWarehouseScopingTests(APITestCase):
    """
    Régression : StockMovementViewSet n'appliquait aucun filtrage par
    magasin — un compte magasin pouvait consulter l'historique des
    mouvements de tous les magasins, pas seulement le sien.
    """

    url = '/api/stock/movements/'

    def setUp(self):
        self.mag1 = User.objects.create_user(username='mag1', password='pass', role=User.ROLE_MAGASINIER)
        self.mag2 = User.objects.create_user(username='mag2', password='pass', role=User.ROLE_MAGASINIER)
        self.dg   = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.wh1  = Warehouse.objects.create(code='WH-A', name='Magasin A', manager=self.mag1)
        self.wh2  = Warehouse.objects.create(code='WH-B', name='Magasin B', manager=self.mag2)
        self.product = Product.objects.create(
            code='PRD-SCOPE', designation='Produit scoping', unit='pcs',
            stock_actuel=Decimal('100'), stock_securite=Decimal('5'),
        )
        StockMovement.objects.create(
            product=self.product, warehouse=self.wh1, movement_type=StockMovement.ENTRY,
            quantity=Decimal('10'), date='2026-01-01',
        )
        StockMovement.objects.create(
            product=self.product, warehouse=self.wh2, movement_type=StockMovement.ENTRY,
            quantity=Decimal('10'), date='2026-01-01',
        )

    def test_magasinier_sees_only_own_warehouse_movements(self):
        self.client.force_authenticate(self.mag1)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get('results', res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['warehouse_code'], 'WH-A')

    def test_dg_sees_all_movements(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get('results', res.data)
        self.assertEqual(len(data), 2)
