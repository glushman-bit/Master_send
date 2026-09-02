from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthTestCase(APITestCase):
    def register(self, **overrides):
        data = {
            'username': 'ivan',
            'email': 'ivan@example.com',
            'first_name': 'Иван',
            'last_name': 'Петров',
            'phone': '+79990000000',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        data.update(overrides)
        return self.client.post('/api/auth/register/', data, format='json')

    def test_register_returns_tokens(self):
        res = self.register()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', res.data['tokens'])
        self.assertIn('refresh', res.data['tokens'])
        self.assertEqual(res.data['user']['username'], 'ivan')

    def test_register_password_mismatch(self):
        res = self.register(password_confirm='wrong')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_requires_all_fields(self):
        res = self.register(first_name='')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('first_name', res.data)

        res = self.register(phone='')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)

    def test_register_invalid_phone(self):
        res = self.register(phone='not-a-phone')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)

    def test_register_duplicate_email(self):
        self.register()
        res = self.register(username='ivan2', email='IVAN@example.com')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)

    def test_register_duplicate_username(self):
        self.register()
        res = self.register(username='ivan', email='other@example.com')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', res.data)

    def test_register_simple_password_accepted(self):
        res = self.register(password='123456', password_confirm='123456')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_login_by_username(self):
        self.register()
        res = self.client.post('/api/auth/login/', {
            'username': 'ivan',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['tokens'])

    def test_login_by_email(self):
        self.register()
        res = self.client.post('/api/auth/login/', {
            'username': 'IVAN@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['tokens'])

    def test_login_wrong_password(self):
        self.register()
        res = self.client.post('/api/auth/login/', {
            'username': 'ivan',
            'password': 'wrong',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile(self):
        tokens = self.register().data['tokens']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'ivan')

    def test_change_password(self):
        tokens = self.register().data['tokens']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.post('/api/auth/change-password/', {
            'old_password': 'StrongPass123!',
            'new_password': 'NewStrongPass456!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.client.credentials()
        login = self.client.post('/api/auth/login/', {
            'username': 'ivan',
            'password': 'NewStrongPass456!',
        }, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_old(self):
        tokens = self.register().data['tokens']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.post('/api/auth/change-password/', {
            'old_password': 'nope',
            'new_password': 'NewStrongPass456!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CreateSuperuserCommandTestCase(TestCase):
    def setUp(self):
        from unittest.mock import patch
        self.patcher = patch.dict('os.environ', {
            'ADMIN_USERNAME': 'boss',
            'ADMIN_EMAIL': 'boss@example.com',
            'ADMIN_PASSWORD': 'topsecret',
        })
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_creates_superuser(self):
        call_command('csu')
        user = User.objects.get(username='boss')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, 'boss@example.com')
        self.assertTrue(user.check_password('topsecret'))

    def test_updates_existing_superuser(self):
        user = User.objects.create_user(username='boss', password='old')
        user.is_superuser = True
        user.is_staff = True
        user.save()

        call_command('csu')
        user.refresh_from_db()
        self.assertEqual(user.email, 'boss@example.com')
        self.assertTrue(user.check_password('topsecret'))

    def test_defaults_when_env_missing(self):
        import os
        for k in ('ADMIN_USERNAME', 'ADMIN_PASSWORD'):
            os.environ.pop(k, None)
        call_command('csu')
        user = User.objects.get(username='admin')
        self.assertTrue(user.check_password('admin'))