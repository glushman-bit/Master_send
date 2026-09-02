from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from core.tests_utils import TempMediaMixin
from portfolio.models import PortfolioItem
from services.models import Service


class PortfolioTestCase(TempMediaMixin, APITestCase):
    def setUp(self):
        """Создаёт опубликованную и скрытую работу портфолио."""
        super().setUp()
        service = Service.objects.create(
            category=Service.Category.SAND,
            title='Пескоструй',
            description='Обработка',
            price_from=1000,
        )
        gif = SimpleUploadedFile('after.gif', b'GIF89a', content_type='image/gif')
        PortfolioItem.objects.create(
            service=service, title='Диски до/после', image_after=gif, is_published=True,
        )
        PortfolioItem.objects.create(
            service=service, title='Скрытая работа', image_after=gif, is_published=False,
        )

    def test_lists_only_published(self):
        """API возвращает только опубликованные работы."""
        res = self.client.get('/api/portfolio/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in res.data['results']]
        self.assertIn('Диски до/после', titles)
        self.assertNotIn('Скрытая работа', titles)