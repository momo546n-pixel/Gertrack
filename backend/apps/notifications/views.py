from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]
    # ← Retire OrderingFilter pour éviter le conflit avec le slice
    # On gère l'ordre manuellement dans get_queryset

    def get_queryset(self):
        qs = Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')  # ← ordre fixe ici

        # Filtre non lues
        unread = self.request.query_params.get('unread')
        if unread == 'true':
            qs = qs.filter(is_read=False)

        # Filtre catégorie
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        # ← Slice APRÈS tous les filtres et l'ordre
        return qs[:50]

    def list(self, request, *args, **kwargs):
        """
        Override list pour éviter que DRF essaie de ré-ordonner
        après le slice.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # ── Compteur non lues ─────────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({'count': count})

    # ── Marquer une notif comme lue ───────────────────────────────────────────
    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = timezone.now()
            notif.save(update_fields=['is_read', 'read_at'])
        return Response({'status': 'ok'})

    # ── Marquer toutes comme lues ─────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({'marked': updated})

    # ── Supprimer toutes les lues ─────────────────────────────────────────────
    @action(detail=False, methods=['delete'], url_path='clear-read')
    def clear_read(self, request):
        deleted, _ = Notification.objects.filter(
            recipient=request.user, is_read=True
        ).delete()
        return Response({'deleted': deleted})