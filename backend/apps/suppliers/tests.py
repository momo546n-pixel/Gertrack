from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Supplier


class SupplierPermissionTests(APITestCase):
    """
    Régression : SupplierViewSet n'avait aucun contrôle de rôle sur
    create/update/destroy. Seuls le DG et le Responsable Achat et Logistique gèrent les
    fournisseurs ; tous les rôles authentifiés peuvent les consulter
    (nécessaire pour créer une demande d'achat).
    """

    url = '/api/suppliers/'

    def setUp(self):
        self.dg         = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock      = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.magasinier = User.objects.create_user(username='mag1', password='pass', role=User.ROLE_MAGASINIER)
        self.supplier = Supplier.objects.create(name='Fournisseur Test')

    def test_magasinier_cannot_create_supplier(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(self.url, {'name': 'Hack Fournisseur'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_cannot_update_supplier(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.patch(f'{self.url}{self.supplier.id}/', {'name': 'Hack'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_cannot_delete_supplier(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.delete(f'{self.url}{self.supplier.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.supplier.refresh_from_db()
        self.assertTrue(self.supplier.is_active)

    def test_stock_can_create_supplier(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.url, {'name': 'Nouveau Fournisseur'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_dg_can_create_supplier(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.url, {'name': 'Nouveau Fournisseur DG'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_any_authenticated_role_can_list_suppliers(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
