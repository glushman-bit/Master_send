from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import OrderRequest
from services.models import Service

User = get_user_model()


class OrderTestCase(APITestCase):
    def setUp(self):
        """Создаёт услугу, клиента и мастера для тестов заявок."""
        self.service = Service.objects.create(
            category=Service.Category.SAND,
            title='Пескоструй дисков',
            description='Обработка дисков',
            price_from=1500,
        )
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )

    def post_order(self, **overrides):
        """Отправляет POST-запрос на создание заявки с указанными переопределениями."""
        data = {
            'name': 'Иван',
            'phone': '+79990000000',
            'message': 'Нужен пескоструй',
            'service': self.service.id,
        }
        data.update(overrides)
        return self.client.post('/api/orders/', data, format='json')

    def test_anon_cannot_create_order(self):
        """Неавторизованный пользователь не может создать заявку."""
        res = self.post_order()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(OrderRequest.objects.count(), 0)

    def test_auth_client_can_create_order(self):
        """Авторизованный клиент может создать заявку."""
        self.client.force_authenticate(self.client_user)
        res = self.post_order()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user'], self.client_user.id)

    def test_admin_order_includes_service_title(self):
        """Админский список заявок содержит название выбранной услуги."""
        self.client.force_authenticate(self.client_user)
        order = OrderRequest.objects.create(
            name='Иван', phone='+70000000000', message='xxx',
            service=self.service, user=self.client_user,
        )
        from django.contrib.auth import get_user_model
        user_model = get_user_model()
        self.client.force_authenticate(user_model.objects.create_superuser(
            username='boss', password='Pass123!', email='boss@mail.ru'
        ))
        res = self.client.get('/api/orders/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        found = next((o for o in (res.data.get('results') or res.data) if o['id'] == order.id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found['service_title'], self.service.title)

    def test_master_cannot_create_order(self):
        """Мастер не может создать заявку."""
        self.client.force_authenticate(self.master)
        res = self.post_order()
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(OrderRequest.objects.count(), 0)

    def test_superuser_cannot_create_order(self):
        """Суперпользователь не может создать заявку."""
        admin = User.objects.create_superuser(
            username='admin', password='Pass123!', email='admin@mail.ru'
        )
        self.client.force_authenticate(admin)
        res = self.post_order()
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(OrderRequest.objects.count(), 0)

    def test_model_rejects_master_user(self):
        """Модель отклоняет заявку от мастера при валидации."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from orders.models import OrderRequest as OR
        order = OR(
            name='Иван', phone='+70000000000', message='xxx',
            service=self.service, user=self.master,
        )
        with self.assertRaises(DjangoValidationError):
            order.full_clean()

    def test_client_sees_only_own_orders(self):
        """Клиент видит только свои заявки."""
        self.client.force_authenticate(self.client_user)
        self.post_order()
        OrderRequest.objects.create(
            name='Другой', phone='+70000000000', message='xxx', service=self.service,
            user=self.master,
        )
        res = self.client.get('/api/orders/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

    def test_master_sees_all_orders(self):
        """Мастер видит все заявки."""
        self.client.force_authenticate(self.client_user)
        self.post_order()
        OrderRequest.objects.create(
            name='Другой', phone='+70000000000', message='xxx', service=self.service,
            user=self.client_user,
        )
        self.client.force_authenticate(self.master)
        res = self.client.get('/api/orders/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)

    def test_master_can_update_status(self):
        """Мастер может изменить статус заявки."""
        self.client.force_authenticate(self.client_user)
        self.post_order()
        order = OrderRequest.objects.first()
        self.client.force_authenticate(self.master)
        res = self.client.post(f'/api/orders/{order.id}/status/', {'status': 'progress'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderRequest.Status.IN_PROGRESS)

    def test_client_cannot_update_status(self):
        """Клиент не может изменить статус заявки."""
        self.client.force_authenticate(self.client_user)
        self.post_order()
        order = OrderRequest.objects.first()
        res = self.client.post(f'/api/orders/{order.id}/status/', {'status': 'progress'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_anon_cannot_list_orders(self):
        """Неавторизованный пользователь не может получить список заявок."""
        res = self.client.get('/api/orders/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_master(self):
        """Статистика по статусам доступна мастеру."""
        self.client.force_authenticate(self.client_user)
        self.post_order()
        self.post_order()
        OrderRequest.objects.create(
            name='Другой', phone='+70000000000', message='xxx', service=self.service,
            user=self.client_user,
            status=OrderRequest.Status.IN_PROGRESS,
        )
        self.client.force_authenticate(self.master)
        res = self.client.get('/api/orders/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['new'], 2)
        self.assertEqual(res.data['in_progress'], 1)
        self.assertEqual(res.data['total'], 3)

    def test_stats_forbidden_for_client_and_anon(self):
        """Статистика запрещена клиенту и неавторизованному пользователю."""
        self.client.force_authenticate(self.client_user)
        self.assertEqual(self.client.get('/api/orders/stats/').status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/orders/stats/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_filter(self):
        """Фильтрация заявок по статусу работает."""
        self.client.force_authenticate(self.client_user)
        self.post_order()
        OrderRequest.objects.create(
            name='В работе', phone='+70000000000', message='xxx', service=self.service,
            user=self.client_user,
            status=OrderRequest.Status.IN_PROGRESS,
        )
        self.client.force_authenticate(self.master)
        res = self.client.get('/api/orders/', {'status': 'progress'})
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['status'], 'progress')

    def test_master_is_superuser(self):
        """Суперпользователь считается мастером и получает доступ к статистике."""
        admin = User.objects.create_superuser(
            username='admin', password='Pass123!', email='admin@mail.ru'
        )
        self.client.force_authenticate(admin)
        res = self.client.get('/api/orders/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)