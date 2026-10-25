from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Supplier
from .serializers import SupplierSerializer, SupplierListSerializer
from apps.accounts.models import AuditLog


def _can_manage_suppliers(user):
    """Seuls le DG et le Responsable Achat et Logistique gèrent les fournisseurs — les
    autres rôles ne font que les consulter (nécessaire pour les demandes d'achat)."""
    return getattr(user, 'is_dg', False) or user.role in ('dg', 'stock')


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class   = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'contact_person', 'email', 'city']
    ordering_fields    = ['name', 'city', 'created_at']

    def get_queryset(self):
        return Supplier.objects.filter(is_active=True)

    def perform_create(self, serializer):
        if not _can_manage_suppliers(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent ajouter un fournisseur.")
        supplier = serializer.save()
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_CREATE,
            'Supplier',
            supplier.id,
            f"Fournisseur ajouté : {supplier.name}"
        )

    def perform_update(self, serializer):
        if not _can_manage_suppliers(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent modifier un fournisseur.")
        supplier = serializer.save()
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_UPDATE,
            'Supplier',
            supplier.id,
            f"Fournisseur modifié : {supplier.name}"
        )

    def perform_destroy(self, instance):
        if not _can_manage_suppliers(self.request.user):
            raise PermissionDenied("Seuls le DG et le Responsable Achat et Logistique peuvent désactiver un fournisseur.")
        instance.is_active = False
        instance.save()
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_DELETE,
            'Supplier',
            instance.id,
            f"Fournisseur désactivé : {instance.name}"
        )

    @action(detail=False, methods=['get'], url_path='select-list')
    def select_list(self, request):
        """Liste allégée pour les menus déroulants"""
        qs = Supplier.objects.filter(is_active=True).order_by('name')
        serializer = SupplierListSerializer(qs, many=True)
        return Response(serializer.data)