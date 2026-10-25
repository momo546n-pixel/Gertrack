from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F

from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from apps.accounts.models import AuditLog


def _can_manage_catalog(user):
    """Seuls le DG et le Responsable Achat et Logistique gèrent le catalogue (produits,
    catégories) — les autres rôles ne font que le consulter (nécessaire pour
    créer des demandes)."""
    return getattr(user, 'is_dg', False) or user.role in ('dg', 'stock')


class CategoryViewSet(viewsets.ModelViewSet):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['name']

    def perform_create(self, serializer):
        if not _can_manage_catalog(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent gérer les catégories.")
        serializer.save()

    def perform_update(self, serializer):
        if not _can_manage_catalog(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent gérer les catégories.")
        serializer.save()

    def perform_destroy(self, instance):
        if not _can_manage_catalog(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent gérer les catégories.")
        instance.delete()


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class   = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['category', 'is_active']
    search_fields      = ['code', 'designation']
    ordering_fields    = ['code', 'designation', 'stock_actuel', 'created_at']

    def get_queryset(self):
        # Responsable Financier : jamais besoin de consulter le catalogue
        # (contrairement aux autres rôles, il ne crée jamais de demande —
        # voir UnifiedRequestViewSet.perform_create) — hors périmètre
        # (Évolution 7 — audit UX/sécurité).
        if getattr(self.request.user, 'is_financial_officer', False):
            return Product.objects.none()
        return Product.objects.select_related('category').filter(is_active=True)

    def perform_create(self, serializer):
        if not _can_manage_catalog(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent créer un produit.")
        product = serializer.save()
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_CREATE,
            'Product',
            product.id,
            f"Création produit {product.code} — {product.designation}"
        )

    def perform_update(self, serializer):
        if not _can_manage_catalog(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent modifier un produit.")
        product = serializer.save()
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_UPDATE,
            'Product',
            product.id,
            f"Modification produit {product.code}"
        )

    def perform_destroy(self, instance):
        if not _can_manage_catalog(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent désactiver un produit.")
        # Soft delete — on désactive le produit
        instance.is_active = False
        instance.save()
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_DELETE,
            'Product',
            instance.id,
            f"Désactivation produit {instance.code}"
        )

    # ── Actions personnalisées ──────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        """Produits en dessous du stock de sécurité"""
        if getattr(request.user, 'is_financial_officer', False):
            raise PermissionDenied("Le Responsable Financier n'a pas accès aux données de stock.")
        qs = Product.objects.filter(
            is_active=True,
            stock_actuel__lte=F('stock_securite')
        ).select_related('category')
        serializer = self.get_serializer(qs, many=True)
        return Response({
            'count':   qs.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Statistiques globales du stock"""
        if getattr(request.user, 'is_financial_officer', False):
            raise PermissionDenied("Le Responsable Financier n'a pas accès aux données de stock.")
        total    = Product.objects.filter(is_active=True).count()
        critique = Product.objects.filter(
            is_active=True,
            stock_actuel__lte=F('stock_securite'),
            stock_actuel__gt=0
        ).count()
        rupture  = Product.objects.filter(is_active=True, stock_actuel=0).count()

        return Response({
            'total_produits':  total,
            'stock_ok':        total - critique - rupture,
            'stock_critique':  critique,
            'stock_rupture':   rupture,
        })