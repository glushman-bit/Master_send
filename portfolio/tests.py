import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from core.tests_utils import TempMediaMixin
from portfolio.models import PortfolioImage, PortfolioItem
from services.models import Service

TINY_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


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

    def test_creates_thumb_and_exposes_it_in_api(self):
        """Для загруженного изображения создаётся эскиз и возвращается в API."""
        item = PortfolioItem.objects.get(title='Диски до/после')
        img = PortfolioImage.objects.create(
            item=item,
            kind='before',
            image=SimpleUploadedFile('real.png', TINY_PNG, content_type='image/png'),
        )
        img.refresh_from_db()
        self.assertTrue(img.thumb)
        self.assertTrue(img.thumb.name.endswith('_thumb.jpg'))

        res = self.client.get('/api/portfolio/')
        result = next(p for p in res.data['results'] if p['title'] == 'Диски до/после')
        found = next(im for im in result['images'] if im['id'] == img.id)
        self.assertIn('thumb', found)
        self.assertTrue(found['thumb'].startswith('http'))
