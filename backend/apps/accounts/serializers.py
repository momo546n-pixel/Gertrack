from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, AuditLog, AdminRequest


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Ajoute les infos utilisateur dans le token JWT"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role']      = user.role
        token['full_name'] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        data['user'] = {
            'id':                    self.user.id,
            'username':              self.user.username,
            'email':                 self.user.email,
            'role':                  self.user.role,
            'full_name':             self.user.get_full_name() or self.user.username,
            'is_dg':                 self.user.is_dg,
            'is_ops_chief':          self.user.is_ops_chief,
            'is_project_manager':    self.user.is_project_manager,
            'can_manage_operations': self.user.can_manage_operations,
        }

        AuditLog.log(
            self.user,
            AuditLog.ACTION_LOGIN,
            'User',
            self.user.id,
            f"Connexion de {self.user.username}"
        )
        return data


class UserSerializer(serializers.ModelSerializer):
    is_dg = serializers.ReadOnlyField()

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name',
                  'last_name', 'role', 'phone', 'is_dg']
        read_only_fields = ['id']


class ProjectManagerSerializer(serializers.ModelSerializer):
    """Gestion directe des comptes Chef de Projet (DOP/DG) — Phase B."""
    full_name = serializers.SerializerMethodField()
    password  = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'is_active', 'date_joined', 'last_login', 'password',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password or len(password) < 6:
            raise serializers.ValidationError({'password': 'Un mot de passe de 6 caractères minimum est requis.'})
        user = User(role=User.ROLE_PM, **validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop('username', None)  # le nom d'utilisateur n'est pas modifiable
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            if len(password) < 6:
                raise serializers.ValidationError({'password': 'Un mot de passe de 6 caractères minimum est requis.'})
            instance.set_password(password)
        instance.save()
        return instance


class MagasinierAccountSerializer(serializers.ModelSerializer):
    """
    Gestion (hors création) des comptes de magasin par le DG — Administration
    > Comptes. Chaque magasin possède obligatoirement son propre compte de
    connexion : il ne peut plus être créé indépendamment d'un magasin (voir
    WarehouseViewSet.perform_create et AdminRequest._approve_warehouse_creation) ;
    ce serializer couvre la modification (informations du gérant + identifiant)
    et la réinitialisation de mot de passe d'un compte existant.
    """
    full_name      = serializers.SerializerMethodField()
    warehouse_name = serializers.SerializerMethodField()
    warehouse_code = serializers.SerializerMethodField()
    password       = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'is_active', 'date_joined', 'last_login',
            'warehouse_name', 'warehouse_code', 'password',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def _warehouse(self, obj):
        # related_name='managed_warehouses' sur Warehouse.manager (titulaire)
        return obj.managed_warehouses.first()

    def get_warehouse_name(self, obj):
        wh = self._warehouse(obj)
        return wh.name if wh else None

    def get_warehouse_code(self, obj):
        wh = self._warehouse(obj)
        return wh.code if wh else None

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            if len(password) < 6:
                raise serializers.ValidationError({'password': 'Un mot de passe de 6 caractères minimum est requis.'})
            instance.set_password(password)
        instance.save()
        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    user_name      = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model  = AuditLog
        fields = ['id', 'user_name', 'action', 'action_display', 'model_name',
                  'object_id', 'description', 'ip_address', 'created_at',
                  'field_name', 'old_value', 'new_value']


# ─────────────────────────────────────────────────────────────────────────────
# DEMANDES ADMINISTRATIVES (création/suppression de magasin, etc.)
# ─────────────────────────────────────────────────────────────────────────────

class AdminRequestSerializer(serializers.ModelSerializer):
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display        = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name      = serializers.SerializerMethodField()
    reviewed_by_name       = serializers.SerializerMethodField()

    class Meta:
        model  = AdminRequest
        fields = [
            'id', 'reference', 'request_type', 'request_type_display',
            'payload', 'status', 'status_display',
            'requested_by', 'requested_by_name',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_comment',
            'result_model', 'result_object_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'reference', 'status', 'requested_by',
            'reviewed_by', 'reviewed_at', 'result_model', 'result_object_id',
        ]

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name() or obj.requested_by.username
        return None

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.username
        return None

    def validate(self, data):
        request_type = data.get('request_type')
        payload       = data.get('payload') or {}

        if request_type == AdminRequest.TYPE_WAREHOUSE_CREATION:
            required = ['name', 'code', 'username']
            missing  = [f for f in required if not payload.get(f)]
            if missing:
                raise serializers.ValidationError({
                    'payload': f"Champs manquants : {', '.join(missing)}"
                })
            if 'password' in payload:
                raise serializers.ValidationError({
                    'payload': "Le mot de passe ne doit pas être inclus ici : il sera défini par le DG à la validation."
                })
            from apps.stock.models import Warehouse
            if Warehouse.objects.filter(code=payload['code']).exists():
                raise serializers.ValidationError({'payload': "Ce code de magasin existe déjà."})
            if User.objects.filter(username=payload['username']).exists():
                raise serializers.ValidationError({'payload': "Ce nom d'utilisateur existe déjà."})

        elif request_type == AdminRequest.TYPE_WAREHOUSE_DELETION:
            from apps.stock.models import Warehouse
            warehouse_id = payload.get('warehouse_id')
            if not warehouse_id or not Warehouse.objects.filter(pk=warehouse_id, is_active=True).exists():
                raise serializers.ValidationError({'payload': "Magasin introuvable ou déjà inactif."})
            if AdminRequest.objects.filter(
                request_type=AdminRequest.TYPE_WAREHOUSE_DELETION,
                status=AdminRequest.STATUS_PENDING,
                payload__warehouse_id=warehouse_id,
            ).exists():
                raise serializers.ValidationError({
                    'payload': "Une demande de suppression est déjà en attente pour ce magasin."
                })

        elif request_type == AdminRequest.TYPE_PM_CREATION:
            required = ['username']
            missing  = [f for f in required if not payload.get(f)]
            if missing:
                raise serializers.ValidationError({
                    'payload': f"Champs manquants : {', '.join(missing)}"
                })
            if 'password' in payload:
                raise serializers.ValidationError({
                    'payload': "Le mot de passe ne doit pas être inclus ici : il sera défini par le DG à la validation."
                })
            if User.objects.filter(username=payload['username']).exists():
                raise serializers.ValidationError({'payload': "Ce nom d'utilisateur existe déjà."})

        elif request_type == AdminRequest.TYPE_PM_DELETION:
            user_id = payload.get('user_id')
            if not user_id or not User.objects.filter(pk=user_id, role=User.ROLE_PM, is_active=True).exists():
                raise serializers.ValidationError({'payload': "Chef de projet introuvable ou déjà désactivé."})
            if AdminRequest.objects.filter(
                request_type=AdminRequest.TYPE_PM_DELETION,
                status=AdminRequest.STATUS_PENDING,
                payload__user_id=user_id,
            ).exists():
                raise serializers.ValidationError({
                    'payload': "Une demande de suppression est déjà en attente pour ce compte."
                })

        else:
            raise serializers.ValidationError({'request_type': "Type de demande non pris en charge."})

        return data