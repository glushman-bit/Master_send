from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class AdminPanelViewTestCase(TestCase):
    def setUp(self):
        """Создаёт клиента, мастера и администратора для тестов панели."""
        self.client = Client()
        self.client_user = User.objects.create_user(username='client', password='Pass123!', email='client@mail.ru')
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )
        self.admin = User.objects.create_superuser(username='admin', password='Pass123!', email='admin@mail.ru')

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
        self.assertIn('admin-panel.js', content)

    def login_via_api(self, username):
        """Выполняет вход через API и оставляет сессию в тестовом клиенте."""
        return self.client.post(
            '/api/auth/login/',
            {
                'username': username,
                'password': 'Pass123!',
            },
            format='json',
        )

    def test_admin_panel_opens_after_api_login_for_master(self):
        """После входа через API мастер видит панель администратора (серверный guard)."""
        res = self.login_via_api('master')
        self.assertEqual(res.status_code, 200)
        res = self.client.get('/admin-panel/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Панель администратора')

    def test_admin_panel_redirects_after_api_login_for_client(self):
        """После входа через API клиент всё равно не видит панель администратора."""
        res = self.login_via_api('client')
        self.assertEqual(res.status_code, 200)
        res = self.client.get('/admin-panel/')
        self.assertEqual(res.status_code, 302)
