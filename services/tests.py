from rest_framework import status
from rest_framework.test import APITestCase

from services.models import Service


class ServiceTestCase(APITestCase):
    def setUp(self):
        """Создаёт активную и неактивную услугу для тестов."""
        Service.objects.create(
            category=Service.Category.SAND,
            title='Пескоструй',
            description='Обработка',
            price_from=1000,
            is_active=True,
        )
        Service.objects.create(
            category=Service.Category.WELD,
            title='Сварка (неактивна)',
            description='Скрытая',
            price_from=500,
            is_active=False,
        )

    def test_lists_only_active(self):
        """API возвращает только активные услуги."""
        res = self.client.get('/api/services/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [s['title'] for s in res.data['results']]
        self.assertIn('Пескоструй', titles)
        self.assertNotIn('Сварка (неактивна)', titles)

    def test_filter_by_category(self):
        """Фильтрация услуг по категории работает."""
        res = self.client.get('/api/services/', {'category': 'weld'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)

    def test_category_display_present(self):
        """Поле category_display присутствует в ответе."""
        res = self.client.get('/api/services/')
        self.assertEqual(res.data['results'][0]['category_display'], 'Пескоструй')
