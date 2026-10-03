from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from contacts.models import ContactPage

User = get_user_model()


class ContactPublicTestCase(APITestCase):
    def test_returns_empty_content_when_no_page(self):
        """Без записи API отдаёт пустую контактную информацию."""
        res = self.client.get('/api/contacts/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['phone'], '')
        self.assertEqual(res.data['email'], '')

    def test_returns_published_page(self):
        """Публичное API отдаёт данные опубликованной записи."""
        ContactPage.objects.create(phone='+7 (999) 111-22-33', email='a@b.ru', is_published=True)
        hidden = ContactPage.objects.create(phone='+7 (111) 000-00-00', is_published=False)

        res = self.client.get('/api/contacts/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['phone'], '+7 (999) 111-22-33')
        self.assertEqual(res.data['email'], 'a@b.ru')
        self.assertNotEqual(res.data['phone'], hidden.phone)
        self.assertEqual(res.headers.get('Cache-Control'), 'no-store')


class ContactAdminTestCase(APITestCase):
    def setUp(self):
        """Создаёт клиента и мастера."""
        super().setUp()
        self.client_user = User.objects.create_user(username='client', password='Pass123!', email='client@mail.ru')
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )

    def test_admin_get_forbidden_for_client(self):
        """Клиенту запрещено читать редактируемые контакты."""
        self.client.force_authenticate(self.client_user)
        res = self.client.get('/api/admin/contacts/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_get_requires_auth(self):
        """Аноним не может читать редактируемые контакты."""
        res = self.client.get('/api/admin/contacts/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_get_creates_empty_page(self):
        """Мастер получает контакты, создавая пустую запись при необходимости."""
        self.client.force_authenticate(self.master)
        res = self.client.get('/api/admin/contacts/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['phone'], '')
        self.assertTrue(ContactPage.objects.exists())

    def test_master_can_update_contacts(self):
        """Мастер обновляет контактную информацию."""
        self.client.force_authenticate(self.master)
        res = self.client.put(
            '/api/admin/contacts/',
            {
                'phone': '+7 (999) 123-45-67',
                'email': 'info@master-send.ru',
                'address': 'г. Москва, ул. Мастеровая, д. 1',
                'work_hours': 'Пн–Сб, с 10:00 до 19:00',
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        page = ContactPage.objects.get()
        self.assertEqual(page.phone, '+7 (999) 123-45-67')
        self.assertEqual(page.email, 'info@master-send.ru')
        self.assertEqual(page.address, 'г. Москва, ул. Мастеровая, д. 1')
        self.assertEqual(page.work_hours, 'Пн–Сб, с 10:00 до 19:00')

    def test_master_can_unpublish(self):
        """Мастер может скрыть контакты с сайта."""
        self.client.force_authenticate(self.master)
        orig = ContactPage.objects.create(phone='+7 (999) 123-45-67', is_published=True)
        res = self.client.put('/api/admin/contacts/', {'is_published': 'false'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        orig.refresh_from_db()
        self.assertFalse(orig.is_published)
        public = self.client.get('/api/contacts/')
        self.assertEqual(public.data['phone'], '')
