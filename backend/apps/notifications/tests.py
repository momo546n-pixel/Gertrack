import asyncio

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from gertrack.asgi import application

from .models import Notification
from .utils import _create_notif


class NotificationConsumerTests(TransactionTestCase):
    """
    Phase G V2.1 (§9) : le centre de notifications pousse les événements en
    temps réel via WebSocket (Django Channels), authentifié par JWT — le
    projet utilise l'authentification par token, pas les sessions Django,
    donc AuthMiddlewareStack ne s'applique pas : l'authentification est
    vérifiée manuellement dans NotificationConsumer.connect().
    """

    def setUp(self):
        self.user = User.objects.create_user(username='wsuser', password='pass', role=User.ROLE_DG)

    def test_connect_with_valid_token(self):
        asyncio.run(self._connect_with_valid_token())

    async def _connect_with_valid_token(self):
        token = str(AccessToken.for_user(self.user))
        communicator = WebsocketCommunicator(application, f'/ws/notifications/?token={token}')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    def test_connect_rejected_without_token(self):
        asyncio.run(self._connect_rejected_without_token())

    async def _connect_rejected_without_token(self):
        communicator = WebsocketCommunicator(application, '/ws/notifications/')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    def test_connect_rejected_with_invalid_token(self):
        asyncio.run(self._connect_rejected_with_invalid_token())

    async def _connect_rejected_with_invalid_token(self):
        communicator = WebsocketCommunicator(application, '/ws/notifications/?token=garbage')
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    def test_notification_pushed_in_realtime(self):
        asyncio.run(self._notification_pushed_in_realtime())

    async def _notification_pushed_in_realtime(self):
        token = str(AccessToken.for_user(self.user))
        communicator = WebsocketCommunicator(application, f'/ws/notifications/?token={token}')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await database_sync_to_async(_create_notif)(
            recipient=self.user, category='systeme', notif_type='compte_cree',
            title='Titre test', message='Message test',
        )

        response = await communicator.receive_json_from(timeout=2)
        self.assertEqual(response['title'], 'Titre test')
        self.assertEqual(response['notif_type'], 'compte_cree')

        await communicator.disconnect()


class NotificationTriggerTests(TransactionTestCase):
    """Vérifie que les notifications précédemment définies mais jamais
    déclenchées le sont désormais (demande administrative soumise, compte
    créé) — et que l'échéance projet fonctionne via la commande dédiée."""

    def setUp(self):
        self.dg    = User.objects.create_user(username='dg', password='pass', role=User.ROLE_DG)
        self.stock = User.objects.create_user(username='stock', password='pass', role=User.ROLE_STOCK)

    def test_admin_request_submission_notifies_dg(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(self.stock)
        res = client.post('/api/accounts/admin-requests/', {
            'request_type': 'creation_magasin',
            'payload': {'name': 'Magasin Notif', 'code': 'MAG-NOTIF', 'username': 'mag_notif'},
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(
            Notification.objects.filter(recipient=self.dg, notif_type='demande_admin_soumise').exists()
        )

    def test_approving_warehouse_creation_notifies_new_magasinier(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(self.stock)
        res = client.post('/api/accounts/admin-requests/', {
            'request_type': 'creation_magasin',
            'payload': {'name': 'Magasin Notif 2', 'code': 'MAG-NOTIF2', 'username': 'mag_notif2'},
        }, format='json')
        request_id = res.data['id']

        client.force_authenticate(self.dg)
        res = client.post(f'/api/accounts/admin-requests/{request_id}/approve/', {'password': 'dgDefinedPass1'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)

        new_user = User.objects.get(username='mag_notif2')
        self.assertTrue(
            Notification.objects.filter(recipient=new_user, notif_type='compte_cree').exists()
        )

    def test_check_project_deadlines_command_notifies_dg_and_pm(self):
        import datetime
        from django.core.management import call_command
        from apps.operations.models import Project

        pm = User.objects.create_user(username='pm', password='pass', role=User.ROLE_PM)
        Project.objects.create(
            code='PRJ-DEADLINE', name='Projet Échéance', project_manager=pm,
            status=Project.STATUS_ACTIVE,
            planned_end_date=datetime.date.today() + datetime.timedelta(days=3),
        )

        call_command('check_project_deadlines', days=7)

        self.assertTrue(Notification.objects.filter(recipient=pm, notif_type='echeance_proche').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.dg, notif_type='echeance_proche').exists())
