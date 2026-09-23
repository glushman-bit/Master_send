import io
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from core.tests_utils import TempMediaMixin
from about.models import AboutPage, AboutImage

User = get_user_model()


def make_image(name='about.png', color=(245, 158, 11)):
    """Создаёт валидный PNG-файл для загрузки в ImageField."""
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), color).save(buf, 'PNG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/png')


class AboutPublicTestCase(TempMediaMixin, APITestCase):
    def test_returns_empty_content_when_no_page(self):
        """Без страницы API отдаёт пустое содержимое."""
        res = self.client.get('/api/about/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['description'], '')
        self.assertEqual(res.data['images'], [])

    def test_returns_published_page_with_images(self):
        """Публичное API отдаёт описание и фотографии опубликованной страницы."""
        page = AboutPage.objects.create(description='Мы — команда мастеров.', is_published=True)
        AboutImage.objects.create(page=page, image=make_image('a.png'), order=0)
        AboutImage.objects.create(page=page, image=make_image('b.png'), order=1)
        hidden = AboutPage.objects.create(description='Черновик', is_published=False)
        AboutImage.objects.create(page=hidden, image=make_image('c.png'), order=0)

        res = self.client.get('/api/about/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['description'], 'Мы — команда мастеров.')
        self.assertEqual(len(res.data['images']), 2)


class AboutAdminTestCase(TempMediaMixin, APITestCase):
    def setUp(self):
        """Создаёт клиента и мастера."""
        super().setUp()
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )

    def test_admin_get_forbidden_for_client(self):
        """Клиенту запрещено читать редактируемую страницу «О нас»."""
        self.client.force_authenticate(self.client_user)
        res = self.client.get('/api/admin/about/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_get_requires_auth(self):
        """Аноним не может читать редактируемую страницу «О нас»."""
        res = self.client.get('/api/admin/about/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_get_creates_empty_page(self):
        """Мастер получает страницу «О нас», создавая пустую при необходимости."""
        self.client.force_authenticate(self.master)
        res = self.client.get('/api/admin/about/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['description'], '')
        self.assertTrue(AboutPage.objects.exists())

    def test_master_can_update_with_images(self):
        """Мастер обновляет описание и фотографии."""
        self.client.force_authenticate(self.master)
        res = self.client.put('/api/admin/about/', {
            'description': 'Новый текст о нас',
            'is_published': 'true',
            'images': [make_image('one.png'), make_image('two.png')],
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        page = AboutPage.objects.get()
        self.assertEqual(page.description, 'Новый текст о нас')
        self.assertEqual(page.images.count(), 2)
        self.assertEqual(len(res.data['images']), 2)

    def test_master_can_remove_images(self):
        """Мастер может удалить отдельные фотографии страницы."""
        page = AboutPage.objects.create(description='Текст')
        old = AboutImage.objects.create(page=page, image=make_image('old.png'), order=0)
        self.client.force_authenticate(self.master)
        res = self.client.put('/api/admin/about/', {
            'description': 'Обновлён',
            'remove_images': json.dumps([old.id]),
            'images': [make_image('new.png')],
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        page.refresh_from_db()
        self.assertFalse(page.images.filter(id=old.id).exists())
        self.assertEqual(page.images.count(), 1)

    def test_master_can_set_image_size_and_position(self):
        """Мастер может изменить размер и центрование фото."""
        page = AboutPage.objects.create(description='Текст')
        img = AboutImage.objects.create(page=page, image=make_image('photo.png'), order=0)
        self.client.force_authenticate(self.master)
        res = self.client.put('/api/admin/about/', {
            'description': 'Текст',
            'images_meta': json.dumps([{
                'id': img.id,
                'scale': 150,
                'pos_x': 'left',
                'pos_y': 'bottom',
            }]),
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        img.refresh_from_db()
        self.assertEqual(img.scale, 150)
        self.assertEqual(img.pos_x, 'left')
        self.assertEqual(img.pos_y, 'bottom')
        self.assertEqual(res.data['images'][0]['scale'], 150)
        self.assertEqual(res.data['images'][0]['pos_x'], 'left')
        self.assertEqual(res.data['images'][0]['pos_y'], 'bottom')

    def test_master_can_set_size_and_position_for_new_images(self):
        """Размер и центрование применяются и к новым фотографиям."""
        self.client.force_authenticate(self.master)
        res = self.client.put('/api/admin/about/', {
            'description': 'Текст',
            'images': [make_image('one.png'), make_image('two.png')],
            'images_new_meta': json.dumps([
                {'scale': 250, 'pos_x': 'right', 'pos_y': 'top'},
                {'scale': 80, 'pos_x': 'left', 'pos_y': 'bottom'},
            ]),
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        first, second = AboutImage.objects.order_by('order', 'id')
        self.assertEqual(first.scale, 250)
        self.assertEqual(first.pos_x, 'right')
        self.assertEqual(first.pos_y, 'top')
        self.assertEqual(second.scale, 80)
        self.assertEqual(second.pos_x, 'left')
        self.assertEqual(second.pos_y, 'bottom')

    def test_images_meta_ignores_invalid_values(self):
        """Некорректные значения размера/центрования не применяются."""
        page = AboutPage.objects.create(description='Текст')
        img = AboutImage.objects.create(
            page=page, image=make_image('photo.png'), order=0,
            scale=100, pos_x='center', pos_y='center',
        )
        self.client.force_authenticate(self.master)
        self.client.put('/api/admin/about/', {
            'description': 'Текст',
            'images_meta': json.dumps([{
                'id': img.id,
                'scale': 99999,
                'pos_x': 'diagonal',
                'pos_y': 42,
            }]),
        }, format='multipart')
        img.refresh_from_db()
        self.assertEqual(img.scale, 100)
        self.assertEqual(img.pos_x, 'center')
        self.assertEqual(img.pos_y, 'center')