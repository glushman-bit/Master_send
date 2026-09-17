import io
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from core.tests_utils import TempMediaMixin
from portfolio.models import PortfolioItem, PortfolioImage
from services.models import Service

User = get_user_model()


def make_image(name='img.png', color=(245, 158, 11)):
    """Создаёт валидный PNG-файл для загрузки в ImageField."""
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), color).save(buf, 'PNG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/png')


class PortfolioAdminTestCase(TempMediaMixin, APITestCase):
    def setUp(self):
        """Создаёт услугу, клиента и мастера для тестов управления портфолио."""
        super().setUp()
        self.service = Service.objects.create(
            category=Service.Category.SAND,
            title='Пескоструй',
            description='Обработка',
            price_from=1000,
        )
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )
        self.img_before = make_image('before.png', (30, 80, 200))
        self.img_after = make_image('after.png')

    def test_list_forbidden_for_client(self):
        """Клиент не может получить список работ в админке."""
        self.client.force_authenticate(self.client_user)
        res = self.client.get('/api/admin/portfolio/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_requires_auth(self):
        """Аноним не может получить список работ в админке."""
        res = self.client.get('/api/admin/portfolio/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_master_can_list_all_works(self):
        """Мастер видит в админке и скрытые работы тоже."""
        item = PortfolioItem.objects.create(
            service=self.service, title='Скрытая', is_published=False,
        )
        PortfolioImage.objects.create(
            item=item, kind='after', image=make_image('after.png'),
        )
        self.client.force_authenticate(self.master)
        res = self.client.get('/api/admin/portfolio/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertFalse(res.data['results'][0]['is_published'])

    def test_master_can_create_work_with_many_images(self):
        """Мастер может создать работу с несколькими фото «до» и «после»."""
        self.client.force_authenticate(self.master)
        res = self.client.post('/api/admin/portfolio/', {
            'service': self.service.id,
            'title': 'Новая работа',
            'description': 'Описание',
            'images_after': [self.img_after, make_image('after2.png', (200, 40, 40))],
            'images_before': [self.img_before],
            'is_published': 'true',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item = PortfolioItem.objects.get(title='Новая работа')
        self.assertEqual(item.images.filter(kind='after').count(), 2)
        self.assertEqual(item.images.filter(kind='before').count(), 1)
        kinds = [im['kind'] for im in res.data['images']]
        self.assertEqual(kinds.count('after'), 2)

    def test_master_can_update_work(self):
        """Мастер может изменить работу."""
        item = PortfolioItem.objects.create(
            service=self.service, title='Работа', is_published=True,
        )
        PortfolioImage.objects.create(
            item=item, kind='after', image=make_image('after.png'),
        )
        self.client.force_authenticate(self.master)
        res = self.client.patch(f'/api/admin/portfolio/{item.id}/', {
            'title': 'Изменённая',
            'is_published': 'false',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.title, 'Изменённая')
        self.assertFalse(item.is_published)

    def test_master_can_add_and_remove_images_on_update(self):
        """Мастер может дополнить фото и удалить отдельные изображения."""
        item = PortfolioItem.objects.create(service=self.service, title='Работа')
        old = PortfolioImage.objects.create(
            item=item, kind='before', image=make_image('old.png'),
        )
        self.client.force_authenticate(self.master)
        res = self.client.patch(f'/api/admin/portfolio/{item.id}/', {
            'remove_images': json.dumps([old.id]),
            'images_after': [make_image('new.png')],
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertFalse(item.images.filter(id=old.id).exists())
        self.assertEqual(item.images.filter(kind='after').count(), 1)

    def test_master_can_delete_work(self):
        """Мастер может удалить работу."""
        item = PortfolioItem.objects.create(
            service=self.service, title='На удаление', is_published=True,
        )
        PortfolioImage.objects.create(
            item=item, kind='after', image=make_image('after.png'),
        )
        self.client.force_authenticate(self.master)
        res = self.client.delete(f'/api/admin/portfolio/{item.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PortfolioItem.objects.filter(id=item.id).exists())
        self.assertFalse(PortfolioImage.objects.filter(item_id=item.id).exists())