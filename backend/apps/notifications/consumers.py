import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Pousse les notifications en temps réel à l'utilisateur connecté.

    L'authentification se fait par JWT passé en paramètre de requête
    (`?token=...`), car le projet utilise l'authentification par token
    (SimpleJWT) et non les sessions Django — AuthMiddlewareStack de Channels
    ne s'applique donc pas ici, l'authentification est faite manuellement.
    """

    async def connect(self):
        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4001)
            return

        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ── Réception d'un message poussé depuis _create_notif() ─────────────────
    async def notify(self, event):
        await self.send(text_data=json.dumps(event['data']))

    # ── Authentification JWT (query string) ───────────────────────────────────
    @database_sync_to_async
    def _authenticate(self):
        query_string = parse_qs(self.scope.get('query_string', b'').decode())
        token = (query_string.get('token') or [None])[0]
        if not token:
            return None

        from rest_framework_simplejwt.tokens import AccessToken
        from apps.accounts.models import User

        try:
            validated = AccessToken(token)
            return User.objects.get(pk=validated['user_id'])
        except Exception:
            return None
