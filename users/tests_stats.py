from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import OrderRequest
from services.models import Service

User = get_user_model()


class UserStatsTestCase(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )
        self.admin = User.objects.create_superuser(
            username='admin', password='Pass123!', email='admin@mail.ru'
        )

    def test_stats_requires_auth(self):
        res = self.client.get('/api/auth/stats/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_returns_data(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/auth/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total'], 3)
        self.assertGreaterEqual(res.data['clients'], 1)
        self.assertGreaterEqual(res.data['masters'], 1)
        self.assertIn('new_month', res.data)
        self.assertIn('active_week', res.data)

    def test_client_can_access_stats(self):
        self.client.force_authenticate(self.client_user)
        res = self.client.get('/api/auth/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_user_list_requires_auth(self):
        res = self.client.get('/api/auth/users/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_returns_order_counts(self):
        service = Service.objects.create(
            category=Service.Category.SAND, title='Пескоструй', description='x', price_from=1000,
        )
        OrderRequest.objects.create(
            name='A', phone='+7', message='x', service=service,
            status=OrderRequest.Status.NEW, user=self.admin,
        )
        OrderRequest.objects.create(
            name='B', phone='+7', message='x', service=service,
            status=OrderRequest.Status.NEW, user=self.admin,
        )
        OrderRequest.objects.create(
            name='C', phone='+7', message='x', service=service,
            status=OrderRequest.Status.IN_PROGRESS, user=self.admin,
        )

        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/auth/users/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

        admin_row = next(u for u in res.data if u['id'] == self.admin.id)
        self.assertEqual(admin_row['orders']['total'], 3)
        self.assertEqual(admin_row['orders']['new'], 2)
        self.assertEqual(admin_row['orders']['progress'], 1)
        self.assertEqual(admin_row['orders']['done'], 0)
        self.assertEqual(admin_row['orders']['cancelled'], 0)
        self.assertIn('username', admin_row)
        self.assertIn('email', admin_row)
