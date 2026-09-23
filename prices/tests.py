from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from prices.models import PriceTable

User = get_user_model()


class PricePublicTestCase(APITestCase):
    """Публичный вывод таблиц цен."""

    def test_empty_list(self):
        """Пустая база возвращает пустой список."""
        res = self.client.get('/api/prices/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_only_published_and_ordered(self):
        """В публичный список попадают только опубликованные таблицы в порядке сортировки."""
        PriceTable.objects.create(title='Скрытая', is_published=False, order=0)
        PriceTable.objects.create(title='Первая', order=1)
        PriceTable.objects.create(title='Вторая', order=2)
        res = self.client.get('/api/prices/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [t['title'] for t in res.data]
        self.assertEqual(titles, ['Первая', 'Вторая'])

    def test_public_contains_cells(self):
        """Публичный ответ содержит ячейки таблицы."""
        PriceTable.objects.create(
            title='Покраска дисков',
            cells=[['Диаметр', 'Цена'], ['До D10', '5000,00']],
        )
        res = self.client.get('/api/prices/')
        self.assertEqual(res.data[0]['cells'], [['Диаметр', 'Цена'], ['До D10', '5000,00']])


class PriceAdminTestCase(APITestCase):
    """Права и CRUD таблиц цен в админке."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client', password='Pass123!', email='client@mail.ru'
        )
        self.master = User.objects.create_user(
            username='master', password='Pass123!', email='master@mail.ru', role='master'
        )

    def test_list_requires_auth(self):
        """Анонимному пользователю доступ к админке цен запрещён."""
        res = self.client.get('/api/admin/prices/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_forbidden_for_client(self):
        """Клиент не может управлять таблицами цен."""
        self.client.force_authenticate(self.client_user)
        res = self.client.get('/api/admin/prices/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_master_can_create_and_normalize_cells(self):
        """Мастер создаёт таблицу; строки дополняются до одинаковой ширины."""
        self.client.force_authenticate(self.master)
        res = self.client.post('/api/admin/prices/', {
            'title': 'Покраска дисков',
            'description': 'Цена включает пескоструй и покраску.',
            'order': 1,
            'is_published': True,
            'cells': [['Диаметр', 'Легкосплав'], ['До D10', '5000,00']],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        table = PriceTable.objects.get(title='Покраска дисков')
        self.assertEqual(table.normalized_cells(), [['Диаметр', 'Легкосплав'], ['До D10', '5000,00']])

    def test_invalid_cells_rejected(self):
        """Некорректный формат cells отклоняется."""
        self.client.force_authenticate(self.master)
        res = self.client.post('/api/admin/prices/', {
            'title': 'Плохая таблица',
            'cells': 'not-a-list',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res2 = self.client.post('/api/admin/prices/', {
            'title': 'Плохая таблица',
            'cells': [['ОК'], 'bad-row'],
        }, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_master_can_update_and_delete(self):
        """Мастер обновляет содержимое и удаляет таблицу."""
        table = PriceTable.objects.create(
            title='Старая', cells=[['A', 'B'], ['1', '2']],
        )
        self.client.force_authenticate(self.master)
        res = self.client.put(f'/api/admin/prices/{table.id}/', {
            'title': 'Новая',
            'description': '',
            'order': 5,
            'is_published': False,
            'cells': [['Только заголовок']],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        table.refresh_from_db()
        self.assertEqual(table.title, 'Новая')
        self.assertFalse(table.is_published)
        self.assertEqual(table.normalized_cells(), [['Только заголовок']])

        del_res = self.client.delete(f'/api/admin/prices/{table.id}/')
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PriceTable.objects.filter(id=table.id).exists())