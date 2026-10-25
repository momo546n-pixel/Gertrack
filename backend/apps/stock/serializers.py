from rest_framework import serializers
from .models import Warehouse, StockMovement


# ─────────────────────────────────────────────────────────────────────────────
# WAREHOUSE SERIALIZERS (V2)
#
# Chaque magasin possède directement son propre compte de connexion (le
# "gérant", relation 1-1 via Warehouse.manager) — les informations du gérant
# sont exposées ici en lecture pour préremplir les formulaires côté frontend ;
# leur modification passe par WarehouseViewSet.perform_update /
# reset_password (jamais directement via ce serializer, pour garder le
# contrôle des règles de validation — unicité de l'identifiant, mot de passe).
# ─────────────────────────────────────────────────────────────────────────────

class WarehouseSerializer(serializers.ModelSerializer):
    manager_name       = serializers.SerializerMethodField()
    manager_username   = serializers.SerializerMethodField()
    manager_first_name = serializers.SerializerMethodField()
    manager_last_name  = serializers.SerializerMethodField()
    manager_phone      = serializers.SerializerMethodField()
    manager_email      = serializers.SerializerMethodField()
    manager_is_active  = serializers.SerializerMethodField()
    products_count     = serializers.ReadOnlyField()
    total_movements    = serializers.ReadOnlyField()

    class Meta:
        model  = Warehouse
        fields = [
            'id', 'code', 'name', 'location', 'phone', 'email', 'description',
            'manager', 'manager_name', 'manager_username', 'manager_first_name',
            'manager_last_name', 'manager_phone', 'manager_email', 'manager_is_active',
            'is_active', 'products_count', 'total_movements',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_manager_name(self, obj):
        return (obj.manager.get_full_name() or obj.manager.username) if obj.manager else None

    def get_manager_username(self, obj):
        return obj.manager.username if obj.manager else None

    def get_manager_first_name(self, obj):
        return obj.manager.first_name if obj.manager else ''

    def get_manager_last_name(self, obj):
        return obj.manager.last_name if obj.manager else ''

    def get_manager_phone(self, obj):
        return obj.manager.phone if obj.manager else ''

    def get_manager_email(self, obj):
        return obj.manager.email if obj.manager else ''

    def get_manager_is_active(self, obj):
        return obj.manager.is_active if obj.manager else None



class StockMovementSerializer(serializers.ModelSerializer):
    product_name          = serializers.CharField(source='product.designation', read_only=True)
    product_code          = serializers.CharField(source='product.code', read_only=True)
    product_unit          = serializers.CharField(source='product.unit', read_only=True)
    product_stock_actuel  = serializers.DecimalField(
                                source='product.stock_actuel',
                                max_digits=12, decimal_places=2,
                                read_only=True
                            )
    warehouse_name        = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_code        = serializers.CharField(source='warehouse.code', read_only=True)
    created_by_name       = serializers.SerializerMethodField()
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    origin_display        = serializers.CharField(source='get_origin_display', read_only=True)

    class Meta:
        model  = StockMovement
        fields = [
            'id',
            'product', 'product_name', 'product_code',
            'product_unit', 'product_stock_actuel',
            'warehouse', 'warehouse_name', 'warehouse_code',
            'movement_type', 'movement_type_display',
            'quantity',
            'stock_before', 'stock_after',
            'origin', 'origin_display', 'origin_ref',
            'destination', 'notes', 'date',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'stock_before', 'stock_after']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def validate(self, data):
        movement_type = data.get('movement_type')
        product       = data.get('product')
        quantity      = data.get('quantity', 0)

        # Vérification stock insuffisant pour les sorties
        if movement_type == StockMovement.EXIT and product:
            if product.stock_actuel < quantity:
                raise serializers.ValidationError({
                    'quantity': (
                        f"Stock insuffisant. "
                        f"Disponible : {product.stock_actuel} {product.unit}"
                    )
                })

        # Quantité ajustement ne peut pas être négative
        if movement_type == StockMovement.ADJUSTMENT and quantity < 0:
            raise serializers.ValidationError({
                'quantity': "La quantité d'ajustement ne peut pas être négative."
            })

        return data


class StockMovementListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes"""
    product_code        = serializers.CharField(source='product.code',       read_only=True)
    product_designation = serializers.CharField(source='product.designation', read_only=True)
    movement_type_label = serializers.CharField(source='get_movement_type_display', read_only=True)

    class Meta:
        model  = StockMovement
        fields = [
            'id', 'product_code', 'product_designation',
            'movement_type', 'movement_type_label',
            'quantity', 'stock_before', 'stock_after',
            'destination', 'date', 'created_at',
        ]