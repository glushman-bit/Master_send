from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserBlockTestCase(APITestCase):
    def setUp(self):
        """Создаёт клиента, мастера и администратора для тестов блокировки."""
        self.client_user = User.objects.create_user(username='client', password='Pass123!', email='client@mail.ru')
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )
        self.admin = User.objects.create_superuser(username='admin', password='Pass123!', email='admin@mail.ru')

    def test_block_requires_auth(self):
        """Аноним не может блокировать пользователей."""
        res = self.client.post(f'/api/auth/users/{self.client_user.id}/block/', {'is_active': False})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_cannot_block(self):
        """Клиент не может блокировать пользователей."""
        self.client.force_authenticate(self.client_user)
        res = self.client.post(f'/api/auth/users/{self.client_user.id}/block/', {'is_active': False})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_master_can_block_client(self):
        """Мастер может заблокировать клиента."""
        self.client.force_authenticate(self.master)
        res = self.client.post(
            f'/api/auth/users/{self.client_user.id}/block/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.get(pk=self.client_user.id).is_active)
        self.assertIn('заблокирован', res.data['detail'].lower())

    def test_master_can_unblock_client(self):
        """Мастер может разблокировать клиента."""
        self.client_user.is_active = False
        self.client_user.save(update_fields=['is_active'])
        self.client.force_authenticate(self.master)
        res = self.client.post(
            f'/api/auth/users/{self.client_user.id}/block/',
            {'is_active': True},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(pk=self.client_user.id).is_active)

    def test_cannot_block_superuser(self):
        """Нельзя заблокировать суперпользователя."""
        self.client.force_authenticate(self.master)
        res = self.client.post(
            f'/api/auth/users/{self.admin.id}/block/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.get(pk=self.admin.id).is_active)

    def test_cannot_block_self(self):
        """Нельзя заблокировать собственный аккаунт."""
        self.client.force_authenticate(self.master)
        res = self.client.post(
            f'/api/auth/users/{self.master.id}/block/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_user_returns_404(self):
        """При попытке заблокировать несуществующего пользователя — 404."""
        self.client.force_authenticate(self.master)
        res = self.client.post('/api/auth/users/9999/block/', {'is_active': False})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_list_contains_is_active(self):
        """Список пользователей содержит поле is_active."""
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/auth/users/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        row = next(u for u in res.data if u['id'] == self.client_user.id)
        self.assertIn('is_active', row)
        self.assertTrue(row['is_active'])

    def test_blocked_user_gets_401_on_api(self):
        """Заблокированный пользователь с валидным JWT получает 401 на запросах к API."""
        tokens = RefreshToken.for_user(self.client_user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {tokens.access_token}'}
        # До блокировки — запрос проходит
        res = self.client.get('/api/auth/me/', **headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Блокируем
        self.client_user.is_active = False
        self.client_user.save(update_fields=['is_active'])

        # После блокировки — 401 даже с живым токеном
        res = self.client.get('/api/auth/me/', **headers)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
