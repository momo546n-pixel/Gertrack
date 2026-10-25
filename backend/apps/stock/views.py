
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction, IntegrityError
from django.db.models import Sum, F
from django.utils import timezone

from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from apps.accounts.models import User, AuditLog
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Warehouse, StockMovement
from .serializers import StockMovementSerializer, StockMovementListSerializer, WarehouseSerializer


# ─────────────────────────────────────────────────────────────────────────────
# WAREHOUSE VIEWS (V2)
# ─────────────────────────────────────────────────────────────────────────────

class WarehouseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    # ← Retire filterset_fields qui causait l'erreur sur is_active
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'code', 'location']
    ordering_fields    = ['name', 'code']

    def get_serializer_class(self):
        return WarehouseSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = Warehouse.objects.all()

        # Responsable Financier : hors périmètre (Évolution 7 — audit
        # UX/sécurité) — ne gère jamais le stock ni les magasins.
        if getattr(user, 'is_financial_officer', False):
            return Warehouse.objects.none()

        # Magasinier → uniquement son propre magasin (relation 1-1)
        if user.role == User.ROLE_MAGASINIER:
            qs = qs.filter(manager=user)
            if self.action == 'list':
                qs = qs.filter(is_active=True)
            return qs

        # Le filtre is_active ne s'applique qu'au listing : les actions sur un
        # magasin précis (retrieve, update, reactivate...) doivent pouvoir
        # cibler un magasin désactivé (ex : le réactiver).
        if self.action == 'list':
            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                qs = qs.filter(is_active=is_active.lower() == 'true')
            else:
                qs = qs.filter(is_active=True)

        return qs

    def perform_create(self, serializer):
        user  = self.request.user
        is_dg = getattr(user, 'is_dg', False) or user.role == 'dg'
        if not is_dg:
            raise PermissionDenied(
                "Seul le DG peut créer un magasin directement. Le Responsable Achat et Logistique doit "
                "soumettre une demande de création via /api/accounts/admin-requests/."
            )

        # Chaque magasin possède obligatoirement son propre compte de
        # connexion (le gérant) — créé et affecté ici même, dans la même
        # opération, avec le mot de passe défini immédiatement (pas de mot
        # de passe temporaire, pas de changement forcé à la première connexion).
        mag_username = (self.request.data.get('mag_username') or '').strip()
        mag_password = self.request.data.get('mag_password') or ''
        if not mag_username or not mag_password:
            raise ValidationError({'mag_username': "L'identifiant et le mot de passe du gérant sont requis."})
        if len(mag_password) < 6:
            raise ValidationError({'mag_password': 'Un mot de passe de 6 caractères minimum est requis.'})
        if User.objects.filter(username=mag_username).exists():
            raise ValidationError({'mag_username': "Ce nom d'utilisateur existe déjà."})

        with transaction.atomic():
            warehouse = serializer.save()

            try:
                magasinier = User.objects.create_user(
                    username   = mag_username,
                    password   = mag_password,
                    first_name = self.request.data.get('mag_first_name', ''),
                    last_name  = self.request.data.get('mag_last_name', ''),
                    email      = self.request.data.get('mag_email', ''),
                    phone      = self.request.data.get('mag_phone', ''),
                    role       = User.ROLE_MAGASINIER,
                )
            except IntegrityError as e:
                raise ValidationError({'mag_username': f"Impossible de créer le compte du magasin : {e}"})

            warehouse.manager = magasinier
            warehouse.save(update_fields=['manager', 'updated_at'])
            AuditLog.log(
                user, AuditLog.ACTION_CREATE, 'User', magasinier.id,
                f"Compte du magasin créé avec {warehouse.code} : {magasinier.username}"
            )

    def perform_update(self, serializer):
        user  = self.request.user
        is_dg = getattr(user, 'is_dg', False) or user.role == 'dg'
        if not (is_dg or user.role == 'stock'):
            raise PermissionDenied("Seul le DG ou le Responsable Achat et Logistique peut modifier un magasin.")

        # Le statut (actif/inactif) ne peut être basculé que par le DG — le
        # Responsable Achat et Logistique ne doit pas pouvoir le modifier via cette route
        # générique (seul le DG dispose des actions dédiées destroy/reactivate).
        if not is_dg:
            serializer.validated_data.pop('is_active', None)

        old_manager = serializer.instance.manager
        instance = serializer.save()

        # ── Traçabilité avant/après (Évolution 8) ───────────────────────────
        # `manager` reste écrivable via le serializer générique (pas encore
        # marqué read_only côté API — hors périmètre de cette évolution, qui
        # se limite à observer/tracer les changements, pas à revoir les
        # permissions existantes). S'il change malgré tout, on le trace ici —
        # voir gertrack.business_rules.AUDIT_TRACKED_FIELDS.
        if instance.manager_id != (old_manager.id if old_manager else None):
            def _manager_label(u):
                return (u.get_full_name() or u.username) if u else None
            AuditLog.log(
                user, AuditLog.ACTION_UPDATE, 'Warehouse', instance.id,
                f"Gérant du magasin {instance.code} réaffecté",
                field_name='manager',
                old_value={'manager': _manager_label(old_manager)},
                new_value={'manager': _manager_label(instance.manager)},
            )

        # Le DG peut, dans la même modale, modifier les informations du
        # gérant (nom, prénom, téléphone, email) et son identifiant.
        if is_dg and instance.manager is not None:
            data          = self.request.data
            manager       = instance.manager
            old_username  = manager.username
            new_username  = (data.get('mag_username') or '').strip()
            changed       = False

            if new_username and new_username != manager.username:
                if User.objects.filter(username=new_username).exclude(pk=manager.pk).exists():
                    raise ValidationError({'mag_username': "Ce nom d'utilisateur existe déjà."})
                manager.username = new_username
                changed = True

            for field, key in [('first_name', 'mag_first_name'), ('last_name', 'mag_last_name'),
                                ('phone', 'mag_phone'), ('email', 'mag_email')]:
                if key in data:
                    setattr(manager, field, data.get(key, ''))
                    changed = True

            if changed:
                manager.save()
                AuditLog.log(
                    user, AuditLog.ACTION_UPDATE, 'User', manager.id,
                    f"Compte du magasin {instance.code} modifié : {manager.username}"
                )
                # ── Traçabilité avant/après (Évolution 8) ───────────────────
                # Changement d'identifiant de connexion du gérant — voir
                # gertrack.business_rules.AUDIT_TRACKED_FIELDS (distinct
                # d'une réaffectation du FK manager lui-même, tracée plus
                # haut dans perform_update).
                if manager.username != old_username:
                    AuditLog.log(
                        user, AuditLog.ACTION_UPDATE, 'Warehouse', instance.id,
                        f"Identifiant du gérant du magasin {instance.code} modifié",
                        field_name='manager_username',
                        old_value={'manager_username': old_username},
                        new_value={'manager_username': manager.username},
                    )

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        is_dg = getattr(request.user, 'is_dg', False) or request.user.role == 'dg'
        if not is_dg:
            return Response({'detail': 'Seul le DG peut réinitialiser le mot de passe du compte.'}, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        if not instance.manager:
            return Response({'detail': "Ce magasin n'a pas de compte associé."}, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get('password', '')
        if not password or len(password) < 6:
            return Response({'detail': 'Un mot de passe de 6 caractères minimum est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        instance.manager.set_password(password)
        instance.manager.save(update_fields=['password'])
        AuditLog.log(
            request.user, AuditLog.ACTION_UPDATE, 'User', instance.manager.id,
            f"Mot de passe réinitialisé (compte du magasin {instance.code}) : {instance.manager.username}"
        )
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})

    def destroy(self, request, *args, **kwargs):
        is_dg = getattr(request.user, 'is_dg', False) or request.user.role == 'dg'
        if not is_dg:
            return Response(
                {'detail': "Seul le DG peut désactiver un magasin. Le Responsable Achat et Logistique peut en proposer la suppression via /api/accounts/admin-requests/."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        if instance.manager:
            instance.manager.is_active = False
            instance.manager.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        is_dg = getattr(request.user, 'is_dg', False) or request.user.role == 'dg'
        if not is_dg:
            return Response({'detail': 'Seul le DG peut réactiver un magasin.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=['is_active', 'updated_at'])
        if instance.manager:
            instance.manager.is_active = True
            instance.manager.save(update_fields=['is_active'])
        return Response(WarehouseSerializer(instance).data)

    @action(detail=True, methods=['delete'], url_path='delete-permanently')
    def delete_permanently(self, request, pk=None):
        """
        Suppression définitive et irréversible du magasin ET du compte
        associé (contrairement à destroy() qui ne fait que désactiver).
        Réservé au DG.
        """
        is_dg = getattr(request.user, 'is_dg', False) or request.user.role == 'dg'
        if not is_dg:
            return Response(
                {'detail': 'Seul le DG peut supprimer définitivement un magasin.'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance          = self.get_object()
        warehouse_label   = f"{instance.code} — {instance.name}"
        magasinier        = instance.manager
        magasinier_username = magasinier.username if magasinier else None

        with transaction.atomic():
            instance.delete()
            if magasinier:
                magasinier.delete()

        AuditLog.log(
            request.user, AuditLog.ACTION_DELETE, 'Warehouse', pk,
            f"Suppression définitive du magasin {warehouse_label}"
            + (f" et du compte {magasinier_username}" if magasinier_username else "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Select list — accessible à TOUS les rôles ─────────────────────────────
    @action(detail=False, methods=['get'], url_path='select-list')
    def select_list(self, request):
        """Liste simplifiée pour les selects frontend."""
        user = request.user

        if user.role == User.ROLE_MAGASINIER:
            warehouses = Warehouse.objects.filter(
                manager=user, is_active=True
            ).values('id', 'name', 'code', 'location')
        else:
            warehouses = Warehouse.objects.filter(
                is_active=True
            ).values('id', 'name', 'code', 'location')

        return Response(list(warehouses))

    # ── Stats magasin ─────────────────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        warehouse = self.get_object()
        from datetime import timedelta
        since = timezone.now() - timedelta(days=30)

        movements = StockMovement.objects.filter(warehouse=warehouse)

        return Response({
            'total_products':    movements.values('product').distinct().count(),
            'recent_entries':    movements.filter(movement_type='entree', created_at__gte=since).count(),
            'recent_exits':      movements.filter(movement_type='sortie', created_at__gte=since).count(),
            'low_stock_products': 0,  # calculé côté produit
        })

    # ── Stock réellement présent dans CE magasin ──────────────────────────────
    # Product.stock_actuel est une quantité globale, pas répartie par magasin —
    # le seul lien produit ↔ magasin est l'historique des StockMovement. On
    # reconstitue donc, pour chaque produit ayant eu au moins un mouvement dans
    # ce magasin, sa quantité courante en rejouant ses mouvements dans l'ordre
    # chronologique (même logique que StockMovement.save(), mais scindée par
    # magasin plutôt qu'au niveau global).
    @action(detail=True, methods=['get'], url_path='current-stock')
    def current_stock(self, request, pk=None):
        warehouse = self.get_object()
        # Ordonné par created_at (et non `date`, librement modifiable par
        # l'utilisateur) pour rejouer les mouvements dans leur séquence réelle
        # d'enregistrement — la même séquence qui a produit le stock global.
        movements = StockMovement.objects.filter(warehouse=warehouse).select_related(
            'product', 'product__category'
        ).order_by('product_id', 'created_at', 'id')

        running  = {}
        products = {}
        for m in movements:
            pid = m.product_id
            products[pid] = m.product
            stock = running.get(pid, 0)
            if m.movement_type == StockMovement.ENTRY:
                stock += m.quantity
            elif m.movement_type == StockMovement.EXIT:
                stock -= m.quantity
            elif m.movement_type == StockMovement.ADJUSTMENT:
                stock = m.quantity
            running[pid] = stock

        results = []
        for pid, stock in running.items():
            product = products[pid]
            if stock <= 0:
                stock_status = Product.STATUS_RUPTURE
            elif stock <= product.stock_securite:
                stock_status = Product.STATUS_CRITIQUE
            else:
                stock_status = Product.STATUS_OK
            results.append({
                'product_id':     pid,
                'code':           product.code,
                'designation':    product.designation,
                'category_name':  product.category.name if product.category_id else None,
                'unit':           product.unit,
                'stock_actuel':   stock,
                'stock_securite': product.stock_securite,
                'stock_status':   stock_status,
            })
        results.sort(key=lambda r: r['designation'])

        return Response({
            'warehouse': {'id': warehouse.id, 'code': warehouse.code, 'name': warehouse.name},
            'products':  results,
        })


# ─────────────────────────────────────────────────────────────────────────────
# MOUVEMENTS DE STOCK — lecture seule
#
# Le module "Mouvements" n'existe plus en tant que point d'entrée : un
# StockMovement ne peut désormais être créé que par
# UnifiedRequest._execute_stock_movements() après validation d'une demande.
# Cette vue reste en lecture seule pour l'historique/les stats (dashboard,
# alertes) mais n'expose plus aucune route de création, modification ou
# suppression.
# ─────────────────────────────────────────────────────────────────────────────

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['movement_type', 'origin', 'product']
    search_fields      = ['product__code', 'product__designation', 'destination', 'origin_ref']
    ordering_fields    = ['date', 'created_at', 'quantity']

    def get_queryset(self):
        qs = StockMovement.objects.select_related('product', 'created_by', 'warehouse')
        user = self.request.user
        # Responsable Financier : hors périmètre (Évolution 7 — audit
        # UX/sécurité) — ne gère jamais les mouvements de stock.
        if getattr(user, 'is_financial_officer', False):
            return StockMovement.objects.none()
        if user.role == User.ROLE_MAGASINIER:
            return qs.filter(warehouse__manager=user)
        return qs

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """Résumé du stock pour le dashboard"""
        if getattr(request.user, 'is_financial_officer', False):
            raise PermissionDenied("Le Responsable Financier n'a pas accès aux données de stock.")

        # Stats produits
        total_produits = Product.objects.filter(is_active=True).count()
        stock_critique = Product.objects.filter(
            is_active=True,
            stock_actuel__lte=F('stock_securite'),
            stock_actuel__gt=0
        ).count()
        stock_rupture = Product.objects.filter(
            is_active=True,
            stock_actuel=0
        ).count()

        # Mouvements du mois en cours
        today     = timezone.now().date()
        first_day = today.replace(day=1)

        entrees_mois = StockMovement.objects.filter(
            movement_type=StockMovement.ENTRY,
            date__gte=first_day
        ).aggregate(total=Sum('quantity'))['total'] or 0

        sorties_mois = StockMovement.objects.filter(
            movement_type=StockMovement.EXIT,
            date__gte=first_day
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # Derniers mouvements
        derniers = StockMovement.objects.select_related(
            'product'
        ).order_by('-created_at')[:5]

        return Response({
            'produits': {
                'total':    total_produits,
                'ok':       total_produits - stock_critique - stock_rupture,
                'critique': stock_critique,
                'rupture':  stock_rupture,
            },
            'mouvements_mois': {
                'entrees': float(entrees_mois),
                'sorties': float(sorties_mois),
            },
            'derniers_mouvements': StockMovementListSerializer(derniers, many=True).data,
        })

    @action(detail=False, methods=['get'], url_path='alertes')
    def alertes(self, request):
        """Produits nécessitant une commande"""
        if getattr(request.user, 'is_financial_officer', False):
            raise PermissionDenied("Le Responsable Financier n'a pas accès aux données de stock.")
        produits = Product.objects.filter(
            is_active=True,
            stock_actuel__lte=F('stock_securite')
        ).select_related('category').order_by('stock_actuel')

        return Response({
            'count':   produits.count(),
            'results': ProductSerializer(produits, many=True).data,
        })