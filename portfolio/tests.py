from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from core.tests_utils import TempMediaMixin
from portfolio.models import PortfolioImage, PortfolioItem
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
        item = PortfolioItem.objects.create(
            service=service,
            title='Диски до/после',
            is_published=True,
        )
        PortfolioImage.objects.create(
            item=item,
            kind='before',
            image=SimpleUploadedFile('before.gif', b'GIF89a', content_type='image/gif'),
        )
        PortfolioImage.objects.create(
            item=item,
            kind='after',
            image=SimpleUploadedFile('after.gif', b'GIF89a', content_type='image/gif'),
        )
        hidden = PortfolioItem.objects.create(
            service=service,
            title='Скрытая работа',
            is_published=False,
        )
        PortfolioImage.objects.create(
            item=hidden,
            kind='after',
            image=SimpleUploadedFile('after2.gif', b'GIF89a', content_type='image/gif'),
        )

    def test_lists_only_published(self):
        """API возвращает только опубликованные работы."""
        res = self.client.get('/api/portfolio/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in res.data['results']]
        self.assertIn('Диски до/после', titles)
        self.assertNotIn('Скрытая работа', titles)

    def test_returns_images_grouped_by_kind(self):
        """API возвращает список фото с типом «до»/«после»."""
        res = self.client.get('/api/portfolio/')
        item = next(p for p in res.data['results'] if p['title'] == 'Диски до/после')
        kinds = [im['kind'] for im in item['images']]
        self.assertEqual(kinds.count('before'), 1)
        self.assertEqual(kinds.count('after'), 1)
        for im in item['images']:
            self.assertTrue(im['image'].startswith('http'))
