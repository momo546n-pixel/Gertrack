from rest_framework import serializers
from gertrack.business_rules import RAL_BUDGET_BLOCK_THRESHOLD_PERCENT
from .models import UnifiedRequest, RequestItem, LogisticsStage, RALBudget


class RequestItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.designation', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    stock_actuel = serializers.DecimalField(
        source='product.stock_actuel', max_digits=12, decimal_places=2, read_only=True
    )
    total_price  = serializers.ReadOnlyField()

    class Meta:
        model  = RequestItem
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'product_unit', 'stock_actuel',
            'quantity', 'unit_price', 'total_price', 'notes',
        ]


class UnifiedRequestListSerializer(serializers.ModelSerializer):
    requested_by_name        = serializers.SerializerMethodField()
    requested_by_role        = serializers.SerializerMethodField()
    request_type_display     = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display           = serializers.CharField(source='get_status_display', read_only=True)
    validation_type_display  = serializers.CharField(source='get_validation_type_display', read_only=True)
    logistics_status_display = serializers.CharField(source='logistics_status_label', read_only=True)
    est_en_retard             = serializers.ReadOnlyField()
    warehouse_name          = serializers.SerializerMethodField()
    supplier_name           = serializers.SerializerMethodField()
    project_name            = serializers.SerializerMethodField()
    items_count             = serializers.SerializerMethodField()
    total_amount            = serializers.ReadOnlyField()
    validated_at             = serializers.SerializerMethodField()

    class Meta:
        model  = UnifiedRequest
        fields = [
            'id', 'reference',
            'request_type', 'request_type_display',
            'validation_type', 'validation_type_display',
            'status', 'status_display',
            'logistics_status', 'logistics_status_display',
            'date_livraison_prevue', 'date_livraison_reelle', 'est_en_retard',
            'warehouse_name', 'supplier_name', 'project_name',
            'requested_by', 'requested_by_name', 'requested_by_role',
            'motif', 'date_needed', 'is_urgent',
            'items_count', 'total_amount', 'budget',
            'validated_at', 'financial_execution_at',
            'created_at', 'updated_at',
        ]

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name() or obj.requested_by.username
        return None

    def get_requested_by_role(self, obj):
        return obj.requested_by.role if obj.requested_by else None

    def get_warehouse_name(self, obj):
        return obj.warehouse.name if obj.warehouse else None

    def get_supplier_name(self, obj):
        if obj.supplier:
            return getattr(obj.supplier, 'nom', None) or getattr(obj.supplier, 'name', str(obj.supplier))
        return None

    def get_project_name(self, obj):
        if obj.project:
            return getattr(obj.project, 'name', None) or getattr(obj.project, 'titre', str(obj.project))
        return None

    def get_items_count(self, obj):
        return obj.items.count()

    def get_validated_at(self, obj):
        """Date de validation effective, quel que soit le circuit emprunté
        (DOP seul, DG seul, ou urgence DOP-ou-DG) — le plus récent des deux
        horodatages non nuls correspond au moment où le statut est passé à
        'validee' (voir UnifiedRequest.validate_dop/validate_dg)."""
        dates = [d for d in (obj.dop_validated_at, obj.dg_validated_at) if d]
        return max(dates) if dates else None


class UnifiedRequestDetailSerializer(serializers.ModelSerializer):
    items                   = RequestItemSerializer(many=True)
    requested_by_name       = serializers.SerializerMethodField()
    requested_by_role       = serializers.SerializerMethodField()
    request_type_display    = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display          = serializers.CharField(source='get_status_display', read_only=True)
    validation_type_display = serializers.CharField(source='get_validation_type_display', read_only=True)
    warehouse_name          = serializers.SerializerMethodField()
    supplier_name           = serializers.SerializerMethodField()
    project_name            = serializers.SerializerMethodField()
    dop_validated_by_name   = serializers.SerializerMethodField()
    dg_validated_by_name    = serializers.SerializerMethodField()
    financial_execution_by_name = serializers.SerializerMethodField()
    total_amount            = serializers.ReadOnlyField()

    # ── Circuit logistique (Phase F — §7/§8) ──────────────────────────────────
    logistics_status_display   = serializers.CharField(source='logistics_status_label', read_only=True)
    logistics_stages           = serializers.SerializerMethodField()
    est_en_retard               = serializers.ReadOnlyField()
    reception_confirmed_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = UnifiedRequest
        fields = [
            'id', 'reference',
            'request_type', 'request_type_display',
            'validation_type', 'validation_type_display',
            'status', 'status_display',
            'warehouse', 'warehouse_name',
            'supplier', 'supplier_name',
            'project', 'project_name',
            'budget', 'is_urgent',
            'requested_by', 'requested_by_name', 'requested_by_role',
            'motif', 'notes', 'date_needed', 'proforma',
            'dop_validated_by', 'dop_validated_by_name',
            'dop_validated_at', 'dop_comment',
            'dg_validated_by', 'dg_validated_by_name',
            'dg_validated_at', 'dg_comment',
            'financial_execution_by', 'financial_execution_by_name',
            'financial_execution_at', 'financial_execution_notes',
            'logistics_status', 'logistics_status_display', 'logistics_stages',
            'date_livraison_prevue', 'date_livraison_reelle', 'est_en_retard',
            'reception_confirmed_by', 'reception_confirmed_by_name', 'reception_confirmed_at',
            'total_amount', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'reference', 'requested_by', 'status', 'budget',
            'dop_validated_by', 'dop_validated_at',
            'dg_validated_by', 'dg_validated_at',
            'financial_execution_by', 'financial_execution_at',
            'logistics_status', 'reception_confirmed_by', 'reception_confirmed_at',
        ]

    def get_logistics_stages(self, obj):
        """Liste ordonnée des étapes actives du circuit logistique de ce type
        de demande, telles que configurées par le RAL (LogisticsStage)."""
        stages = LogisticsStage.objects.filter(request_type=obj.request_type, is_active=True).order_by('order', 'id')
        return [{'value': s.code, 'label': s.label} for s in stages]

    def get_reception_confirmed_by_name(self, obj):
        if obj.reception_confirmed_by:
            return obj.reception_confirmed_by.get_full_name() or obj.reception_confirmed_by.username
        return None

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name() or obj.requested_by.username
        return None

    def get_requested_by_role(self, obj):
        return obj.requested_by.role if obj.requested_by else None

    def get_warehouse_name(self, obj):
        return obj.warehouse.name if obj.warehouse else None

    def get_supplier_name(self, obj):
        if obj.supplier:
            return getattr(obj.supplier, 'nom', None) or getattr(obj.supplier, 'name', str(obj.supplier))
        return None

    def get_project_name(self, obj):
        if obj.project:
            return getattr(obj.project, 'name', None) or getattr(obj.project, 'titre', str(obj.project))
        return None

    def get_dop_validated_by_name(self, obj):
        if obj.dop_validated_by:
            return obj.dop_validated_by.get_full_name() or obj.dop_validated_by.username
        return None

    def get_dg_validated_by_name(self, obj):
        if obj.dg_validated_by:
            return obj.dg_validated_by.get_full_name() or obj.dg_validated_by.username
        return None

    def get_financial_execution_by_name(self, obj):
        if obj.financial_execution_by:
            return obj.financial_execution_by.get_full_name() or obj.financial_execution_by.username
        return None

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request    = UnifiedRequest.objects.create(**validated_data)
        for item_data in items_data:
            RequestItem.objects.create(request=request, **item_data)
        return request

    def update(self, instance, validated_data):
        if instance.status != 'brouillon':
            raise serializers.ValidationError("Seul un brouillon peut être modifié.")
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                RequestItem.objects.create(request=instance, **item_data)
        return instance


class LogisticsStageSerializer(serializers.ModelSerializer):
    """Étape du circuit logistique — gestion réservée au RAL (voir
    LogisticsStageViewSet)."""
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)

    class Meta:
        model  = LogisticsStage
        fields = [
            'id', 'request_type', 'request_type_display', 'code', 'label', 'order',
            'is_reception_stage', 'is_closing_stage', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RALBudgetSerializer(serializers.ModelSerializer):
    """Budget annuel du RAL — créé/modifié exclusivement par le DG, visible
    uniquement par le RAL et le DG (voir RALBudgetViewSet)."""
    montant_consomme     = serializers.ReadOnlyField()
    montant_restant       = serializers.ReadOnlyField()
    pourcentage_consomme = serializers.ReadOnlyField()
    is_threshold_reached  = serializers.ReadOnlyField()
    is_creation_blocked    = serializers.ReadOnlyField()
    created_by_name        = serializers.SerializerMethodField()
    threshold_percent      = serializers.SerializerMethodField()

    class Meta:
        model  = RALBudget
        fields = [
            'id', 'year', 'montant_annuel',
            'montant_consomme', 'montant_restant', 'pourcentage_consomme',
            'is_threshold_reached', 'is_creation_blocked', 'is_manually_unblocked',
            'threshold_percent', 'threshold_notified_at', 'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'is_manually_unblocked', 'threshold_notified_at',
            'created_by', 'created_at', 'updated_at',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_threshold_percent(self, obj):
        """Expose le seuil de blocage (gertrack.business_rules) pour que le
        frontend ne le duplique jamais en dur — source unique de vérité."""
        return RAL_BUDGET_BLOCK_THRESHOLD_PERCENT