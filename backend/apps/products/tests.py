from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Product


class ProductCatalogPermissionTests(APITestCase):
    """
    Régression : ProductViewSet/CategoryViewSet n'avaient aucun contrôle de
    rôle sur create/update/destroy — n'importe quel compte authentifié
    (magasinier, chef de projet...) pouvait créer/modifier/désactiver un
    produit ou une catégorie. Seuls le DG et le Responsable Achat et Logistique gèrent le
    catalogue ; tous les rôles authentifiés peuvent le consulter.
    """

    products_url   = '/api/products/'
    categories_url = '/api/products/categories/'

    def setUp(self):
        self.dg         = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock      = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)
        self.magasinier = User.objects.create_user(username='mag1', password='pass', role=User.ROLE_MAGASINIER)
        self.pm         = User.objects.create_user(username='pm1', password='pass', role=User.ROLE_PM)
        self.product = Product.objects.create(
            code='PRD-1', designation='Produit test', unit='pcs',
            stock_actuel=10, stock_securite=2,
        )

    def _payload(self, code='PRD-NEW'):
        return {'code': code, 'designation': 'Nouveau produit', 'unit': 'pcs', 'stock_actuel': 0, 'stock_securite': 1}

    def test_magasinier_cannot_create_product(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(self.products_url, self._payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Product.objects.filter(code='PRD-NEW').exists())

    def test_pm_cannot_create_product(self):
        self.client.force_authenticate(self.pm)
        res = self.client.post(self.products_url, self._payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_cannot_update_product(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.patch(f'{self.products_url}{self.product.id}/', {'designation': 'Hack'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_magasinier_cannot_delete_product(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.delete(f'{self.products_url}{self.product.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)

    def test_stock_can_create_product(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.products_url, self._payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_dg_can_create_product(self):
        self.client.force_authenticate(self.dg)
        res = self.client.post(self.products_url, self._payload(), format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_any_authenticated_role_can_list_products(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.get(self.products_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_magasinier_cannot_create_category(self):
        self.client.force_authenticate(self.magasinier)
        res = self.client.post(self.categories_url, {'name': 'Hack Category'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_stock_can_create_category(self):
        self.client.force_authenticate(self.stock)
        res = self.client.post(self.categories_url, {'name': 'Nouvelle Catégorie'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
