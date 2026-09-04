from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminPanelViewTestCase(TestCase):
    def setUp(self):
        """Создаёт клиента, мастера и администратора для тестов панели."""
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )
        self.admin = User.objects.create_superuser(
            username='admin', password='Pass123!', email='admin@mail.ru'
        )

    def test_admin_panel_requires_auth(self):
        """Анонимный пользователь не видит панель администратора."""
        res = self.client.get('/admin-panel/')
        self.assertEqual(res.status_code, 302)

    def test_admin_panel_forbidden_for_client(self):
        """Клиент (не мастер) не видит панель администратора."""
        self.client.force_login(self.client_user)
        res = self.client.get('/admin-panel/')
        self.assertEqual(res.status_code, 302)

    def test_admin_panel_renders_for_master(self):
        """Панель администратора доступна мастеру и содержит заголовок."""
        self.client.force_login(self.master)
        res = self.client.get('/admin-panel/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Панель администратора')

    def test_admin_panel_contains_stats_elements(self):
        """Панель администратора содержит элементы статистики."""
        self.client.force_login(self.admin)
        res = self.client.get('/admin-panel/')
        content = res.content.decode()
        self.assertIn('js-users-total', content)
        self.assertIn('js-stat-new', content)
        self.assertIn('auth/stats/', content)