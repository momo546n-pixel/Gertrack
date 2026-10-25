from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    category_display  = serializers.CharField(source='get_category_display',  read_only=True)
    notif_type_display = serializers.CharField(source='get_notif_type_display', read_only=True)
    time_ago           = serializers.SerializerMethodField()

    class Meta:
        model  = Notification
        fields = [
            'id', 'category', 'category_display',
            'notif_type', 'notif_type_display',
            'title', 'message', 'is_read', 'link',
            'object_id', 'created_at', 'read_at', 'time_ago',
        ]
        read_only_fields = ['created_at', 'read_at']

    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        now   = timezone.now()
        delta = now - obj.created_at
        if delta < timedelta(minutes=1):
            return "À l'instant"
        if delta < timedelta(hours=1):
            m = int(delta.total_seconds() // 60)
            return f'Il y a {m} min'
        if delta < timedelta(days=1):
            h = int(delta.total_seconds() // 3600)
            return f'Il y a {h}h'
        if delta < timedelta(days=7):
            return f'Il y a {delta.days}j'
        return obj.created_at.strftime('%d/%m/%Y')