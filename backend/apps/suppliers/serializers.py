from rest_framework import serializers
from .models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    total_orders     = serializers.ReadOnlyField()
    validated_orders = serializers.ReadOnlyField()

    # ── Indicateur de performance (Phase F — §7) ──────────────────────────────
    taux_livraison_a_temps  = serializers.ReadOnlyField()
    delai_moyen_jours       = serializers.ReadOnlyField()
    commandes_en_retard_count = serializers.ReadOnlyField()

    class Meta:
        model  = Supplier
        fields = [
            'id', 'name', 'contact_person', 'phone', 'email',
            'address', 'city', 'notes', 'is_active',
            'total_orders', 'validated_orders',
            'taux_livraison_a_temps', 'delai_moyen_jours', 'commandes_en_retard_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_email(self, value):
        if value and Supplier.objects.filter(
            email=value
        ).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Un fournisseur avec cet email existe déjà.")
        return value


class SupplierListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes déroulantes"""
    class Meta:
        model  = Supplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'city']