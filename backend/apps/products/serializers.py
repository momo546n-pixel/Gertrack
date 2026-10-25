from rest_framework import serializers
from .models import Product, Category


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status  = serializers.ReadOnlyField()
    needs_reorder = serializers.ReadOnlyField()

    class Meta:
        model  = Product
        fields = [
            'id', 'code', 'designation', 'category', 'category_name',
            'unit', 'conditionnement', 'stock_actuel', 'stock_securite',
            'description', 'is_active', 'stock_status', 'needs_reorder',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_code(self, value):
        return value.upper()

    def validate_stock_actuel(self, value):
        if value < 0:
            raise serializers.ValidationError("Le stock ne peut pas être négatif.")
        return value

    def validate_stock_securite(self, value):
        if value < 0:
            raise serializers.ValidationError("Le stock de sécurité ne peut pas être négatif.")
        return value