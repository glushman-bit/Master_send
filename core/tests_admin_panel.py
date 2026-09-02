from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminPanelViewTestCase(TestCase):
    def setUp(self):
        """Создаёт клиента и администратора для тестов панели."""
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.admin = User.objects.create_superuser(
            username='admin', password='Pass123!', email='admin@mail.ru'
        )

    def test_admin_panel_renders(self):
        """Панель администратора рендерится и содержит заголовок."""
        res = self.client.get('/admin-panel/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Панель администратора')

    def test_admin_panel_contains_stats_elements(self):
        """Панель администратора содержит элементы статистики."""
        res = self.client.get('/admin-panel/')
        content = res.content.decode()
        self.assertIn('js-users-total', content)
        self.assertIn('js-stat-new', content)
        self.assertIn('auth/stats/', content)
