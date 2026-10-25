from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.stock.models import Warehouse

from .models import User, AdminRequest, AuditLog


class AdminRequestWarehouseWorkflowTests(APITestCase):
    """
    Un magasin créé par le Responsable Achat et Logistique ne doit jamais exister
    directement — il passe par une AdminRequest validée par le DG, qui crée
    alors le magasin ET son compte de connexion en une seule opération
    atomique. Le mot de passe du compte est toujours défini par le DG au
    moment de l'approbation (même pattern que les comptes chef de projet) —
    jamais par le Responsable Achat et Logistique à la soumission.
    """

    url = '/api/accounts/admin-requests/'

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.other_stock = User.objects.create_user(username='stock2', password='pass', role=User.ROLE_STOCK)

    def _creation_payload(self, code='MAG-1'):
        return {
            'request_type': AdminRequest.TYPE_WAREHOUSE_CREATION,
            'payload': {
                'name': 'Magasin Test', 'code': code, 'location': 'Dakar',
                'phone': '221000000', 'email': 'mag@test.com',
                'username': 'mag_titulaire',
                'first_name': 'Amadou', 'last_name': 'Diop',
                'account_email': 'amadou@test.com', 'account_phone': '221111111',
            },
        }

    # ── Création directe interdite pour le Responsable Achat et Logistique ─────────────────
    def test_stock_cannot_create_warehouse_directly(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post('/api/stock/warehouses/', {'name': 'X', 'code': 'X1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dg_can_still_create_warehouse_directly(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post('/api/stock/warehouses/', {
            'name': 'Direct', 'code': 'DIR-1',
            'mag_username': 'mag_dir1', 'mag_password': 'directPass1',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertTrue(Warehouse.objects.filter(code='DIR-1').exists())

    def test_dg_create_warehouse_requires_account_fields(self):
        # Chaque magasin possède obligatoirement son propre compte : le DG ne
        # peut plus créer un magasin sans fournir l'identifiant/mot de passe.
        self.client.force_authenticate(self.dg)
        res = self.client.post('/api/stock/warehouses/', {'name': 'Sans compte', 'code': 'DIR-0'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Warehouse.objects.filter(code='DIR-0').exists())

    def test_dg_can_create_warehouse_with_magasinier_in_same_request(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post('/api/stock/warehouses/', {
            'name': 'Direct+Mag', 'code': 'DIR-2',
            'mag_username': 'mag_direct', 'mag_first_name': 'Ousmane', 'mag_last_name': 'Fall',
            'mag_password': 'directPass1',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        warehouse = Warehouse.objects.get(code='DIR-2')
        magasinier = User.objects.get(username='mag_direct')
        self.assertEqual(warehouse.manager_id, magasinier.id)
        self.assertTrue(magasinier.check_password('directPass1'))

    def test_dg_create_warehouse_with_short_mag_password_rolls_back(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post('/api/stock/warehouses/', {
            'name': 'Rollback', 'code': 'DIR-3',
            'mag_username': 'mag_rollback', 'mag_password': 'abc',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Warehouse.objects.filter(code='DIR-3').exists())
        self.assertFalse(User.objects.filter(username='mag_rollback').exists())

    # ── Soumission de la demande ──────────────────────────────────────────────
    def test_stock_can_submit_creation_request(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, self._creation_payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'en_attente')
        self.assertFalse(Warehouse.objects.filter(code='MAG-1').exists())
        # Aucun mot de passe n'est soumis ni stocké à cette étape.
        self.assertNotIn('password', res.data['payload'])
        self.assertNotIn('password_hash', res.data['payload'])

    def test_password_in_payload_is_rejected(self):
        self.client.force_authenticate(self.stock)
        payload = self._creation_payload()
        payload['payload']['password'] = 'leaked123'
        res = self.client.post(self.url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_warehouse_code_rejected_at_submission(self):
        Warehouse.objects.create(code='MAG-1', name='Existant')
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, self._creation_payload(code='MAG-1'), format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Validation DG ─────────────────────────────────────────────────────────
    def test_approve_creates_warehouse_and_account_with_dg_defined_password(self):
        self.client.force_authenticate(self.stock)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/approve/', {'password': 'dgDefinedPass1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data['status'], 'validee')

        warehouse = Warehouse.objects.get(code='MAG-1')
        self.assertEqual(warehouse.name, 'Magasin Test')
        self.assertIsNotNone(warehouse.manager)
        self.assertEqual(warehouse.manager.username, 'mag_titulaire')
        self.assertEqual(warehouse.manager.role, User.ROLE_MAGASINIER)

        # Le compte se connecte avec le mot de passe défini par le DG à
        # l'approbation — jamais un mot de passe soumis par le Responsable Achat et Logistique.
        self.assertTrue(warehouse.manager.check_password('dgDefinedPass1'))

    def test_approve_without_password_is_rejected(self):
        self.client.force_authenticate(self.stock)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/approve/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Warehouse.objects.filter(code='MAG-1').exists())

    def test_approve_with_short_password_is_rejected(self):
        self.client.force_authenticate(self.stock)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/approve/', {'password': 'abc'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Warehouse.objects.filter(code='MAG-1').exists())

    def test_non_dg_cannot_approve(self):
        self.client.force_authenticate(self.stock)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        res = self.client.post(f'{self.url}{req_id}/approve/', {'password': 'tempPass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_does_not_create_warehouse(self):
        self.client.force_authenticate(self.stock)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/reject/', {'comment': 'Pas nécessaire'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'refusee')
        self.assertFalse(Warehouse.objects.filter(code='MAG-1').exists())

    # ── Visibilité des demandes ───────────────────────────────────────────────
    def test_stock_only_sees_own_requests(self):
        self.client.force_authenticate(self.stock)
        self.client.post(self.url, self._creation_payload(code='MAG-A'), format='json')

        self.client.force_authenticate(self.other_stock)
        self.client.post(self.url, self._creation_payload(code='MAG-B'), format='json')
        res = self.client.get(self.url)
        self.assertEqual(len(res.data.get('results', res.data)), 1)

    def test_dg_sees_all_requests(self):
        self.client.force_authenticate(self.stock)
        self.client.post(self.url, self._creation_payload(code='MAG-A'), format='json')
        self.client.force_authenticate(self.other_stock)
        self.client.post(self.url, self._creation_payload(code='MAG-B'), format='json')

        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        self.assertEqual(len(res.data.get('results', res.data)), 2)

    # ── Suppression proposée ──────────────────────────────────────────────────
    def test_stock_can_propose_deletion_and_dg_approval_deactivates(self):
        warehouse = Warehouse.objects.create(code='MAG-DEL', name='À supprimer')
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, {
            'request_type': AdminRequest.TYPE_WAREHOUSE_DELETION,
            'payload': {'warehouse_id': warehouse.id},
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.dg)
        res = self.client.post(f"{self.url}{res.data['id']}/approve/", {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        warehouse.refresh_from_db()
        self.assertFalse(warehouse.is_active)

    # ── Réactivation d'un magasin désactivé ───────────────────────────────────
    def test_dg_can_reactivate_deactivated_warehouse(self):
        warehouse = Warehouse.objects.create(code='MAG-REACT', name='Inactif', is_active=False)
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'/api/stock/warehouses/{warehouse.id}/reactivate/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        warehouse.refresh_from_db()
        self.assertTrue(warehouse.is_active)


class AdminRequestProjectManagerWorkflowTests(APITestCase):
    """
    Phase B V2.1 : un compte Chef de Projet créé par le DOP ne doit jamais
    exister directement — il passe par une AdminRequest validée par le DG,
    qui définit le mot de passe à l'approbation (même pattern que les
    magasins en Phase A).
    """

    url = '/api/accounts/admin-requests/'

    def setUp(self):
        self.dg       = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.dop      = User.objects.create_user(username='dop', password='pass', role=User.ROLE_OPS_CHIEF)
        self.other_dop = User.objects.create_user(username='dop2', password='pass', role=User.ROLE_OPS_CHIEF)
        self.stock    = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)

    def _creation_payload(self, username='pm_test'):
        return {
            'request_type': AdminRequest.TYPE_PM_CREATION,
            'payload': {
                'username': username, 'first_name': 'Fatou', 'last_name': 'Ndiaye',
                'email': 'fatou@test.com', 'phone': '221222222',
            },
        }

    def test_dop_can_submit_creation_request(self):
        self.client.force_authenticate(self.dop)
        res = self.client.post(self.url, self._creation_payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(User.objects.filter(username='pm_test').exists())

    def test_stock_cannot_submit_pm_creation_request(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, self._creation_payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_in_payload_is_rejected(self):
        self.client.force_authenticate(self.dop)
        payload = self._creation_payload()
        payload['payload']['password'] = 'leaked123'
        res = self.client.post(self.url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_creates_pm_account_with_dg_defined_password(self):
        self.client.force_authenticate(self.dop)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/approve/', {'password': 'chefProjet123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        pm = User.objects.get(username='pm_test')
        self.assertEqual(pm.role, User.ROLE_PM)
        self.assertTrue(pm.check_password('chefProjet123'))

    def test_reject_does_not_create_account(self):
        self.client.force_authenticate(self.dop)
        create_res = self.client.post(self.url, self._creation_payload(), format='json')
        req_id = create_res.data['id']

        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{req_id}/reject/', {'comment': 'Non nécessaire'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(username='pm_test').exists())

    def test_dop_can_propose_deletion_and_dg_approval_deactivates(self):
        pm = User.objects.create_user(username='pm_existing', password='pass', role=User.ROLE_PM)
        self.client.force_authenticate(self.dop)
        res = self.client.post(self.url, {
            'request_type': AdminRequest.TYPE_PM_DELETION,
            'payload': {'user_id': pm.id},
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.dg)
        res = self.client.post(f"{self.url}{res.data['id']}/approve/", {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        pm.refresh_from_db()
        self.assertFalse(pm.is_active)

    def test_dop_only_sees_own_requests(self):
        self.client.force_authenticate(self.dop)
        self.client.post(self.url, self._creation_payload(username='pm_a'), format='json')
        self.client.force_authenticate(self.other_dop)
        self.client.post(self.url, self._creation_payload(username='pm_b'), format='json')
        res = self.client.get(self.url)
        self.assertEqual(len(res.data.get('results', res.data)), 1)


class ProjectManagerAccountTests(APITestCase):
    """
    Phase B V2.1 : gestion directe des comptes Chef de Projet — création par
    le DG (sans passer par une demande), modification par le DOP ou le DG,
    désactivation/réactivation/suppression réservées au DG.
    """

    url = '/api/accounts/project-managers/'

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.dop   = User.objects.create_user(username='dop', password='pass', role=User.ROLE_OPS_CHIEF)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.pm    = User.objects.create_user(username='pm1', password='pass', role=User.ROLE_PM)

    def test_dg_can_create_directly(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.url, {
            'username': 'pm_direct', 'first_name': 'Awa', 'last_name': 'Sy', 'password': 'directPass1',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        pm = User.objects.get(username='pm_direct')
        self.assertEqual(pm.role, User.ROLE_PM)
        self.assertTrue(pm.check_password('directPass1'))

    def test_dop_cannot_create_directly(self):
        self.client.force_authenticate(self.dop)
        res = self.client.post(self.url, {
            'username': 'pm_direct2', 'password': 'directPass1',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dop_can_modify_existing_account(self):
        self.client.force_authenticate(self.dop)
        res = self.client.patch(f'{self.url}{self.pm.id}/', {'phone': '221333333'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pm.refresh_from_db()
        self.assertEqual(self.pm.phone, '221333333')

    def test_dop_cannot_change_password_via_edit(self):
        self.client.force_authenticate(self.dop)
        res = self.client.patch(f'{self.url}{self.pm.id}/', {'password': 'newPass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.pm.refresh_from_db()
        self.assertFalse(self.pm.check_password('newPass123'))

    def test_dg_can_change_password_via_edit(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.pm.id}/', {'password': 'newPass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pm.refresh_from_db()
        self.assertTrue(self.pm.check_password('newPass123'))

    def test_stock_cannot_view_project_managers(self):
        self.client.force_authenticate(self.stock)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 0)

    def test_dg_can_deactivate_and_reactivate(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{self.pm.id}/deactivate/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pm.refresh_from_db()
        self.assertFalse(self.pm.is_active)

        res = self.client.post(f'{self.url}{self.pm.id}/reactivate/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pm.refresh_from_db()
        self.assertTrue(self.pm.is_active)

    def test_dop_cannot_deactivate(self):
        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{self.pm.id}/deactivate/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dg_can_hard_delete(self):
        self.client.force_authenticate(self.dg)
        res = self.client.delete(f'{self.url}{self.pm.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=self.pm.id).exists())

    def test_dop_cannot_hard_delete(self):
        self.client.force_authenticate(self.dop)
        res = self.client.delete(f'{self.url}{self.pm.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.filter(id=self.pm.id).exists())

    def test_dg_can_reset_password(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{self.pm.id}/reset-password/', {'password': 'newPass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pm.refresh_from_db()
        self.assertTrue(self.pm.check_password('newPass123'))

    def test_dop_cannot_reset_password(self):
        self.client.force_authenticate(self.dop)
        res = self.client.post(f'{self.url}{self.pm.id}/reset-password/', {'password': 'newPass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MagasinierAccountTests(APITestCase):
    """
    Administration > Comptes — vue miroir des comptes de magasin (chaque
    magasin possède obligatoirement son propre compte, créé uniquement via
    Gestion des Magasins ou une demande de création validée par le DG).
    Ce module couvre la modification (informations du gérant + identifiant),
    la désactivation/réactivation (synchronisée avec le magasin), la
    réinitialisation de mot de passe et la suppression définitive (qui
    supprime aussi le magasin associé).
    """

    url = '/api/accounts/magasiniers/'

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.dop   = User.objects.create_user(username='dop', password='pass', role=User.ROLE_OPS_CHIEF)
        self.mag   = User.objects.create_user(username='mag1', password='pass', role=User.ROLE_MAGASINIER)
        self.warehouse = Warehouse.objects.create(code='WH-ADM', name='Magasin Admin', manager=self.mag)

    def test_dg_sees_magasiniers_with_warehouse_context(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get('results', res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['warehouse_code'], 'WH-ADM')

    def test_stock_cannot_view_magasiniers(self):
        self.client.force_authenticate(self.stock)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data.get('results', res.data)), 0)

    def test_cannot_create_directly_anymore(self):
        # Un compte ne peut plus être créé indépendamment d'un magasin.
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.url, {
            'username': 'mag_new', 'password': 'directPass1',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_dg_can_modify(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.mag.id}/', {'phone': '221555555'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.mag.refresh_from_db()
        self.assertEqual(self.mag.phone, '221555555')

    def test_dg_can_modify_username(self):
        self.client.force_authenticate(self.dg)
        res = self.client.patch(f'{self.url}{self.mag.id}/', {'username': 'mag1_renamed'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.mag.refresh_from_db()
        self.assertEqual(self.mag.username, 'mag1_renamed')

    def test_dop_cannot_modify(self):
        # Le DOP n'a aucune visibilité sur les magasiniers (contrairement aux
        # chefs de projet) : get_queryset() renvoie une liste vide, donc
        # l'objet est introuvable (404), pas explicitement refusé (403).
        self.client.force_authenticate(self.dop)
        res = self.client.patch(f'{self.url}{self.mag.id}/', {'phone': '221555555'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_dg_can_deactivate_reactivate_syncs_warehouse(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{self.mag.id}/deactivate/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.mag.refresh_from_db()
        self.warehouse.refresh_from_db()
        self.assertFalse(self.mag.is_active)
        self.assertFalse(self.warehouse.is_active)

        res = self.client.post(f'{self.url}{self.mag.id}/reactivate/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.mag.refresh_from_db()
        self.warehouse.refresh_from_db()
        self.assertTrue(self.mag.is_active)
        self.assertTrue(self.warehouse.is_active)

    def test_dg_can_reset_password(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(f'{self.url}{self.mag.id}/reset-password/', {'password': 'newMagPass1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.mag.refresh_from_db()
        self.assertTrue(self.mag.check_password('newMagPass1'))

    def test_dg_can_hard_delete_account_and_warehouse(self):
        self.client.force_authenticate(self.dg)
        res = self.client.delete(f'{self.url}{self.mag.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=self.mag.id).exists())
        self.assertFalse(Warehouse.objects.filter(id=self.warehouse.id).exists())

    def test_non_dg_cannot_delete(self):
        self.client.force_authenticate(self.stock)
        res = self.client.delete(f'{self.url}{self.mag.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.filter(id=self.mag.id).exists())

    def test_activity_returns_requests_by_type(self):
        from apps.requests.models import UnifiedRequest
        UnifiedRequest.objects.create(request_type='entree', requested_by=self.mag, warehouse=self.warehouse)
        UnifiedRequest.objects.create(request_type='sortie', requested_by=self.mag, warehouse=self.warehouse)
        UnifiedRequest.objects.create(request_type='ajustement', requested_by=self.mag, warehouse=self.warehouse)

        self.client.force_authenticate(self.dg)
        res = self.client.get(f'{self.url}{self.mag.id}/activity/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['entrees']), 1)
        self.assertEqual(len(res.data['sorties']), 1)
        self.assertEqual(len(res.data['ajustements']), 1)


class ProjectManagerActivityTests(APITestCase):
    """
    Phase D V2.1 : fiche détaillée / historique d'activité du chef de projet
    (projets, tâches récentes, reportings, demandes) — réutilise les
    modèles/serializers existants d'apps.operations et apps.requests.
    """

    url = '/api/accounts/project-managers/'

    def setUp(self):
        from apps.operations.models import Project, Task, WeeklyReport
        from apps.requests.models import UnifiedRequest

        self.dg  = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.pm  = User.objects.create_user(username='pm1', password='pass', role=User.ROLE_PM)

        self.project = Project.objects.create(code='PRJ-ACT', name='Projet Activité', project_manager=self.pm)
        Task.objects.create(project=self.project, name='Tâche 1', total_quantity=10, weight=50)
        WeeklyReport.objects.create(
            project=self.project, week_number=1, year=2026, report_date='2026-01-05',
        )
        UnifiedRequest.objects.create(request_type='sortie', requested_by=self.pm, project=self.project)

    def test_activity_returns_projects_tasks_reports_and_requests(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(f'{self.url}{self.pm.id}/activity/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['projets']), 1)
        self.assertEqual(res.data['projets'][0]['code'], 'PRJ-ACT')
        self.assertEqual(len(res.data['taches_recentes']), 1)
        self.assertEqual(len(res.data['reportings']), 1)
        self.assertEqual(len(res.data['demandes']), 1)


class ActivityJournalTests(APITestCase):
    """
    Phase E V2.1 : journal d'activité — connexion/déconnexion tracées, IP
    capturée automatiquement (CurrentRequestMiddleware), consultable par le DG.
    """

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass123', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass123', role=User.ROLE_STOCK)

    def test_login_is_logged_with_ip(self):
        res = self.client.post('/api/accounts/login/', {'username': 'dg', 'password': 'pass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        log = AuditLog.objects.filter(user=self.dg, action=AuditLog.ACTION_LOGIN).latest('created_at')
        self.assertIsNotNone(log.ip_address)

    def test_login_updates_last_login(self):
        # SimpleJWT ne passe pas par django.contrib.auth.login() (pas de
        # session) : sans UPDATE_LAST_LOGIN=True dans SIMPLE_JWT, last_login
        # reste éternellement à None malgré des connexions réelles.
        self.assertIsNone(self.dg.last_login)
        res = self.client.post('/api/accounts/login/', {'username': 'dg', 'password': 'pass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.dg.refresh_from_db()
        self.assertIsNotNone(self.dg.last_login)

    def test_logout_is_logged(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post('/api/accounts/logout/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(user=self.dg, action=AuditLog.ACTION_LOGOUT).exists())

    def test_logout_requires_authentication(self):
        res = self.client.post('/api/accounts/logout/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_action_is_logged_with_ip_without_explicit_request_param(self):
        """
        AuditLog.log() appelé sans `request=` explicite (comme dans la
        quasi-totalité des points d'appel existants) doit tout de même
        capturer l'IP via le middleware.
        """
        self.client.force_authenticate(self.dg)
        res = self.client.post('/api/accounts/project-managers/', {
            'username': 'pm_journal', 'password': 'pass1234',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        log = AuditLog.objects.filter(model_name='User', action=AuditLog.ACTION_CREATE).latest('created_at')
        self.assertIsNotNone(log.ip_address)

    def test_dg_sees_all_logs_others_see_only_their_own(self):
        AuditLog.log(self.dg, AuditLog.ACTION_LOGIN, 'User', self.dg.id, 'x')
        AuditLog.log(self.stock, AuditLog.ACTION_LOGIN, 'User', self.stock.id, 'y')

        self.client.force_authenticate(self.stock)
        res = self.client.get('/api/accounts/audit-logs/')
        data = res.data.get('results', res.data)
        self.assertTrue(all(l['user_name'] == 'stock' for l in data))

        self.client.force_authenticate(self.dg)
        res = self.client.get('/api/accounts/audit-logs/')
        data = res.data.get('results', res.data)
        self.assertGreaterEqual(len(data), 2)


class AuditLogEnrichmentBackwardCompatTests(APITestCase):
    """
    Évolution 8 — AuditLog.log() gagne 3 paramètres optionnels
    (field_name/old_value/new_value) en fin de signature. Aucun des ~55
    appels existants ne doit être affecté : un appel à l'ancienne (sans ces
    paramètres) doit continuer à créer une ligne strictement équivalente à
    avant, avec les nouveaux champs simplement vides/None.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pass', role=User.ROLE_DG)

    def test_old_style_call_still_works_unchanged(self):
        log = AuditLog.log(self.user, AuditLog.ACTION_CREATE, 'Widget', 42, 'Un widget créé')
        self.assertEqual(log.description, 'Un widget créé')
        self.assertEqual(log.field_name, '')
        self.assertIsNone(log.old_value)
        self.assertIsNone(log.new_value)

    def test_new_style_call_with_structured_values(self):
        log = AuditLog.log(
            self.user, AuditLog.ACTION_UPDATE, 'Widget', 42, 'Widget modifié',
            field_name='budget', old_value={'budget': 100}, new_value={'budget': 200},
        )
        self.assertEqual(log.field_name, 'budget')
        self.assertEqual(log.old_value, {'budget': 100})
        self.assertEqual(log.new_value, {'budget': 200})

    def test_existing_call_sites_still_produce_valid_logs(self):
        """Un échantillon d'appels existants (accounts, requests, operations,
        stock, products) doit toujours fonctionner sans exception."""
        res = self.client.post('/api/accounts/login/', {'username': 'u', 'password': 'pass'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        log = AuditLog.objects.filter(user=self.user, action=AuditLog.ACTION_LOGIN).latest('created_at')
        self.assertEqual(log.field_name, '')


class AuditCenterScopingTests(APITestCase):
    """
    Évolution 8 — Centre d'audit : le DG voit tout, chaque autre rôle ne voit
    que son propre périmètre (ses propres actions + les objets dont il est
    responsable), jamais celui des autres. Endpoint additif : n'affecte
    jamais /api/accounts/audit-logs/ (voir tests ci-dessus, toujours verts).
    """

    url = '/api/accounts/audit-center/'

    def setUp(self):
        from apps.operations.models import Project
        from apps.requests.models import UnifiedRequest

        self.dg   = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.pm1  = User.objects.create_user(username='pm1', password='pass', role=User.ROLE_PM)
        self.pm2  = User.objects.create_user(username='pm2', password='pass', role=User.ROLE_PM)
        self.mag1 = User.objects.create_user(username='mag1', password='pass', role=User.ROLE_MAGASINIER)
        self.mag2 = User.objects.create_user(username='mag2', password='pass', role=User.ROLE_MAGASINIER)
        self.financier1 = User.objects.create_user(username='fin1', password='pass', role=User.ROLE_FINANCIAL)
        self.financier2 = User.objects.create_user(username='fin2', password='pass', role=User.ROLE_FINANCIAL)

        self.project1 = Project.objects.create(code='P1', name='Projet PM1', project_manager=self.pm1, created_by=self.dg)
        self.project2 = Project.objects.create(code='P2', name='Projet PM2', project_manager=self.pm2, created_by=self.dg)
        self.warehouse1 = Warehouse.objects.create(code='W1', name='Magasin 1', manager=self.mag1)
        self.warehouse2 = Warehouse.objects.create(code='W2', name='Magasin 2', manager=self.mag2)
        self.req1 = UnifiedRequest.objects.create(request_type='achat', requested_by=self.pm1, project=self.project1)
        self.req2 = UnifiedRequest.objects.create(request_type='achat', requested_by=self.pm2, project=self.project2)
        self.req_w1 = UnifiedRequest.objects.create(request_type='entree', requested_by=self.mag1, warehouse=self.warehouse1)
        self.req_w2 = UnifiedRequest.objects.create(request_type='entree', requested_by=self.mag2, warehouse=self.warehouse2)
        self.req_exec1 = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.pm1, status='executee', financial_execution_by=self.financier1,
        )
        self.req_exec2 = UnifiedRequest.objects.create(
            request_type='achat', requested_by=self.pm2, status='executee', financial_execution_by=self.financier2,
        )

        AuditLog.log(self.dg, AuditLog.ACTION_UPDATE, 'Project', self.project1.id, 'Projet 1 modifié')
        AuditLog.log(self.dg, AuditLog.ACTION_UPDATE, 'Project', self.project2.id, 'Projet 2 modifié')
        AuditLog.log(self.dg, AuditLog.ACTION_UPDATE, 'UnifiedRequest', self.req1.id, 'Req 1 modifiée')
        AuditLog.log(self.dg, AuditLog.ACTION_UPDATE, 'UnifiedRequest', self.req2.id, 'Req 2 modifiée')
        AuditLog.log(self.dg, AuditLog.ACTION_CREATE, 'UnifiedRequest', self.req_w1.id, 'Entrée magasin 1 créée')
        AuditLog.log(self.dg, AuditLog.ACTION_CREATE, 'UnifiedRequest', self.req_w2.id, 'Entrée magasin 2 créée')
        AuditLog.log(self.dg, AuditLog.ACTION_UPDATE, 'Warehouse', self.warehouse1.id, 'Magasin 1 modifié')
        AuditLog.log(self.dg, AuditLog.ACTION_UPDATE, 'Warehouse', self.warehouse2.id, 'Magasin 2 modifié')
        AuditLog.log(self.dg, AuditLog.ACTION_EXECUTE, 'UnifiedRequest', self.req_exec1.id, 'Req exécutée par fin1')
        AuditLog.log(self.dg, AuditLog.ACTION_EXECUTE, 'UnifiedRequest', self.req_exec2.id, 'Req exécutée par fin2')
        AuditLog.log(self.pm1, AuditLog.ACTION_LOGIN, 'User', self.pm1.id, 'Connexion pm1')

    def _object_ids_seen(self, res, model_name):
        data = res.data.get('results', res.data)
        return {row['object_id'] for row in data if row['model_name'] == model_name}

    def test_dg_sees_everything(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get('results', res.data)
        self.assertGreaterEqual(len(data), 9)

    def test_project_manager_sees_only_own_project_never_the_other(self):
        self.client.force_authenticate(self.pm1)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        project_ids = self._object_ids_seen(res, 'Project')
        self.assertIn(str(self.project1.id), project_ids)
        self.assertNotIn(str(self.project2.id), project_ids)
        request_ids = self._object_ids_seen(res, 'UnifiedRequest')
        self.assertIn(str(self.req1.id), request_ids)
        self.assertNotIn(str(self.req2.id), request_ids)
        # Ne voit jamais les magasins ni les exécutions financières d'autrui.
        self.assertEqual(self._object_ids_seen(res, 'Warehouse'), set())

    def test_magasinier_sees_only_own_warehouse_never_the_other(self):
        self.client.force_authenticate(self.mag1)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        warehouse_ids = self._object_ids_seen(res, 'Warehouse')
        self.assertIn(str(self.warehouse1.id), warehouse_ids)
        self.assertNotIn(str(self.warehouse2.id), warehouse_ids)
        request_ids = self._object_ids_seen(res, 'UnifiedRequest')
        self.assertIn(str(self.req_w1.id), request_ids)
        self.assertNotIn(str(self.req_w2.id), request_ids)
        self.assertNotIn(str(self.project1.id), self._object_ids_seen(res, 'Project'))

    def test_financial_officer_sees_only_own_executions(self):
        self.client.force_authenticate(self.financier1)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        request_ids = self._object_ids_seen(res, 'UnifiedRequest')
        self.assertIn(str(self.req_exec1.id), request_ids)
        self.assertNotIn(str(self.req_exec2.id), request_ids)
        # Ne voit ni les projets, ni les magasins, ni les demandes non liées
        # à sa propre exécution — règle identique à l'Évolution 7.
        self.assertEqual(self._object_ids_seen(res, 'Project'), set())
        self.assertEqual(self._object_ids_seen(res, 'Warehouse'), set())
        self.assertNotIn(str(self.req1.id), request_ids)

    def test_filter_by_model_name(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url, {'model_name': 'Warehouse'})
        data = res.data.get('results', res.data)
        self.assertTrue(all(row['model_name'] == 'Warehouse' for row in data))
        self.assertGreaterEqual(len(data), 2)

    def test_filter_by_action(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url, {'action': AuditLog.ACTION_EXECUTE})
        data = res.data.get('results', res.data)
        self.assertTrue(all(row['action'] == AuditLog.ACTION_EXECUTE for row in data))
        self.assertGreaterEqual(len(data), 2)

    def test_filter_by_search(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(self.url, {'search': 'fin1'})
        data = res.data.get('results', res.data)
        self.assertTrue(any('fin1' in row['description'] for row in data))

    def test_csv_export_returns_csv_content(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(f'{self.url}export-csv/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'text/csv; charset=utf-8')
        content = res.content.decode('utf-8')
        self.assertIn('Date', content.splitlines()[0])

    def test_csv_export_respects_role_scoping(self):
        import csv as csv_module
        import io
        self.client.force_authenticate(self.financier1)
        res = self.client.get(f'{self.url}export-csv/')
        rows = list(csv_module.DictReader(io.StringIO(res.content.decode('utf-8'))))
        # Aucune ligne "Project" ne doit fuiter hors du périmètre du financier.
        self.assertFalse(any(row['Modèle'] == 'Project' for row in rows))
        self.assertTrue(any(row['Modèle'] == 'UnifiedRequest' and row['Objet'].endswith(str(self.req_exec1.id)) for row in rows))

    def test_pdf_export_returns_pdf_content(self):
        self.client.force_authenticate(self.dg)
        res = self.client.get(f'{self.url}export-pdf/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/pdf')

    def test_unauthenticated_cannot_access(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
