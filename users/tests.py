import re
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache as django_cache
from django.core.management import call_command
from django.core.signing import TimestampSigner, b62_encode
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from users import services

User = get_user_model()


def make_expired_token(pk):
    """Подписывает токен подтверждения с просроченной меткой времени."""
    old_ts = b62_encode(int(time.time()) - (services.VERIFY_TOKEN_MAX_AGE + 3600))
    signer = TimestampSigner(salt=services.VERIFY_SALT)
    base = f'{pk}:{old_ts}'
    return f'{base}:{signer.signature(base)}'

# Троттлинг DRF хранит счётчики в стандартном кеше, который в проде — Redis.
# В тестах используем локальный кеш и обнуляем его перед каждым тестом,
# чтобы поздние тесты не получали 429 от накопившихся счётчиков.
@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class AuthTestCase(APITestCase):
    def setUp(self):
        """Очищает почтовый ящик и кеш (счётчики троттлинга) перед каждым тестом."""
        mail.outbox.clear()
        django_cache.clear()

    def register(self, **overrides):
        """Отправляет POST-запрос на регистрацию с указанными переопределениями."""
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

    def last_verify_token(self):
        """Достаёт токен подтверждения из последнего отправленного письма."""
        msg = mail.outbox[-1]
        body = msg.body + ' ' + ' '.join(a[0] for a in msg.alternatives)
        m = re.search(r'/verify/\?token=([^\s"<]+)', body)
        self.assertIsNotNone(m, 'В письме нет ссылки подтверждения')
        return m.group(1)

    def verify(self):
        """Подтверждает регистрацию последним письмом и возвращает ответ."""
        return self.client.post(
            '/api/auth/verify-email/',
            {'token': self.last_verify_token()},
            format='json',
        )

    def register_verified(self, **overrides):
        """Регистрирует пользователя и сразу подтверждает email — возвращает JWT-токены."""
        self.register(**overrides)
        res = self.verify()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return res.data['tokens']

    def test_register_sends_verification_and_no_tokens(self):
        """Регистрация создаёт неподтверждённого пользователя и шлёт письмо без выдачи токенов."""
        res = self.register()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('tokens', res.data)
        self.assertIn('detail', res.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/verify/?token=', mail.outbox[0].body)
        user = User.objects.get(username='ivan')
        self.assertFalse(user.email_verified)

    def test_register_password_mismatch(self):
        """Регистрация отклоняется при несовпадении паролей."""
        res = self.register(password_confirm='wrong')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_requires_all_fields(self):
        """Регистрация требует все обязательные поля."""
        res = self.register(first_name='')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('first_name', res.data)

        res = self.register(phone='')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)

    def test_register_invalid_phone(self):
        """Регистрация отклоняет некорректный номер телефона."""
        res = self.register(phone='not-a-phone')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)

    def test_register_duplicate_email(self):
        """Регистрация отклоняет повторное использование email."""
        self.register()
        res = self.register(username='ivan2', email='IVAN@example.com')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)

    def test_register_duplicate_username(self):
        """Регистрация отклоняет повторное использование логина."""
        self.register()
        res = self.register(username='ivan', email='other@example.com')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', res.data)

    def test_register_simple_password_accepted(self):
        """Регистрация принимает простой пароль (мин. длина 6)."""
        res = self.register(password='123456', password_confirm='123456')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_login_unverified_email_rejected_with_code(self):
        """Вход неподтверждённого пользователя запрещён с кодом email_not_verified."""
        self.register()
        res = self.client.post(
            '/api/auth/login/',
            {'username': 'ivan', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get('code'), 'email_not_verified')
        self.assertEqual(res.data.get('email'), 'ivan@example.com')
        self.assertNotIn('access', res.data.get('tokens', {}))

    def test_verify_email_activates_and_returns_tokens(self):
        """Подтверждение по ссылке активирует аккаунт и возвращает JWT-токены."""
        self.register()
        res = self.verify()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['tokens'])
        self.assertTrue(User.objects.get(username='ivan').email_verified)

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'ivan', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_verify_email_invalid_token(self):
        """Подтверждение с невалидным токеном отклоняется с кодом token_invalid."""
        self.register()
        res = self.client.post(
            '/api/auth/verify-email/',
            {'token': 'not-a-real-token'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get('code'), 'token_invalid')
        self.assertFalse(User.objects.get(username='ivan').email_verified)

    def test_verify_email_expired_token_registered_user(self):
        """Истёкший токен для зарегистрированного пользователя даёт код token_expired с user_exists."""
        self.register()
        user = User.objects.get(username='ivan')
        res = self.client.post(
            '/api/auth/verify-email/',
            {'token': make_expired_token(user.pk)},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get('code'), 'token_expired')
        self.assertTrue(res.data.get('user_exists'))
        self.assertEqual(res.data.get('email'), 'ivan@example.com')
        self.assertFalse(User.objects.get(username='ivan').email_verified)

    def test_verify_email_expired_token_unknown_user(self):
        """Истёкший токен для несуществующего пользователя: user_exists=False (нужна регистрация)."""
        res = self.client.post(
            '/api/auth/verify-email/',
            {'token': make_expired_token(999999)},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get('code'), 'token_expired')
        self.assertFalse(res.data.get('user_exists'))

    def test_verify_email_second_click_already_verified(self):
        """Повторный клик по ссылке для подтверждённого email сообщает email_already_verified."""
        self.register()
        self.assertEqual(self.verify().status_code, status.HTTP_200_OK)

        user = User.objects.get(username='ivan')
        res = self.client.post(
            '/api/auth/verify-email/',
            {'token': services.make_verification_token(user)},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.get('code'), 'email_already_verified')
        self.assertNotIn('tokens', res.data)
        self.assertTrue(User.objects.get(username='ivan').email_verified)

    def test_login_by_username(self):
        """Вход по логину работает после подтверждения email."""
        self.register_verified()
        res = self.client.post(
            '/api/auth/login/',
            {'username': 'ivan', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['tokens'])

    def test_login_by_email(self):
        """Вход по email работает."""
        self.register_verified()
        res = self.client.post(
            '/api/auth/login/',
            {'username': 'IVAN@example.com', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['tokens'])

    def test_login_wrong_password(self):
        """Вход с неверным паролем отклоняется."""
        self.register_verified()
        res = self.client.post(
            '/api/auth/login/',
            {'username': 'ivan', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_deactivated_user_rejected(self):
        """Деактивированный пользователь не может войти даже с верным паролем."""
        self.register_verified()
        user = User.objects.get(username='ivan')
        user.is_active = False
        user.save()

        res = self.client.post(
            '/api/auth/login/',
            {'username': 'ivan', 'password': 'StrongPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', res.data.get('tokens', {}))

    def test_resend_verification(self):
        """Повторная отправка шлёт новое письмо с токеном."""
        self.register()
        mail.outbox.clear()
        res = self.client.post(
            '/api/auth/resend-verification/',
            {'email': 'ivan@example.com'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        token = self.last_verify_token()
        self.client.post('/api/auth/verify-email/', {'token': token}, format='json')
        self.assertTrue(User.objects.get(username='ivan').email_verified)

    def test_resend_verification_hides_unknown_email(self):
        """Повторная отправка не раскрывает, зарегистрирован ли email."""
        res = self.client.post(
            '/api/auth/resend-verification/',
            {'email': 'nobody@example.com'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_me_requires_auth(self):
        """Получение профиля требует авторизации."""
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile(self):
        """Авторизованный пользователь получает свой профиль."""
        tokens = self.register_verified()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'ivan')

    def test_profile_update_rejects_duplicate_email(self):
        """Обновление профиля отклоняет email, занятый другим пользователем."""
        self.register()
        petr = User.objects.create_user(username='petr', password='Pass123!', email='petr@example.com')
        petr.email_verified = True
        petr.save()
        tokens = self.client.post(
            '/api/auth/login/',
            {'username': 'petr', 'password': 'Pass123!'},
            format='json',
        ).data['tokens']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        res = self.client.patch(
            '/api/auth/me/',
            {'email': 'IVAN@example.com'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)

    def test_profile_update_keeps_own_email(self):
        """Пользователь может оставить свой email неизменным при обновлении."""
        tokens = self.register_verified()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.patch(
            '/api/auth/me/',
            {'email': 'ivan@example.com', 'first_name': 'Иван'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_change_password(self):
        """Смена пароля работает, после неё вход с новым паролем возможен."""
        tokens = self.register_verified()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.post(
            '/api/auth/change-password/',
            {'old_password': 'StrongPass123!', 'new_password': 'NewStrongPass456!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.client.credentials()
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'ivan', 'password': 'NewStrongPass456!'},
            format='json',
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_old(self):
        """Смена пароля отклоняется при неверном старом пароле."""
        tokens = self.register_verified()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = self.client.post(
            '/api/auth/change-password/',
            {'old_password': 'nope', 'new_password': 'NewStrongPass456!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CreateSuperuserCommandTestCase(TestCase):
    def setUp(self):
        """Задаёт переменные окружения с данными суперпользователя."""
        from unittest.mock import patch

        self.patcher = patch.dict(
            'os.environ',
            {
                'ADMIN_USERNAME': 'boss',
                'ADMIN_EMAIL': 'boss@example.com',
                'ADMIN_PASSWORD': 'topsecret',
            },
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_creates_superuser(self):
        """Команда csu создаёт суперпользователя из переменных окружения."""
        call_command('csu')
        user = User.objects.get(username='boss')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.email, 'boss@example.com')
        self.assertTrue(user.check_password('topsecret'))

    def test_updates_existing_superuser(self):
        """Команда csu обновляет существующего суперпользователя."""
        user = User.objects.create_user(username='boss', password='old')
        user.is_superuser = True
        user.is_staff = True
        user.save()

        call_command('csu')
        user.refresh_from_db()
        self.assertEqual(user.email, 'boss@example.com')
        self.assertTrue(user.check_password('topsecret'))
        self.assertTrue(user.email_verified)

    def test_defaults_when_env_missing(self):
        """При отсутствии переменных окружения используются значения по умолчанию."""
        import os

        for k in ('ADMIN_USERNAME', 'ADMIN_PASSWORD'):
            os.environ.pop(k, None)
        call_command('csu')
        user = User.objects.get(username='admin')
        self.assertTrue(user.check_password('admin'))