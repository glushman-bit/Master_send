from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.tests_utils import TempMediaMixin
from portfolio.models import PortfolioItem
from services.models import Service


class PageTestCase(TestCase):
    def test_home_page(self):
        """Главная страница доступна (200)."""
        res = self.client.get(reverse('core:home'))
        self.assertEqual(res.status_code, 200)

    def test_services_page(self):
        """Страница услуг доступна (200)."""
        res = self.client.get(reverse('core:services'))
        self.assertEqual(res.status_code, 200)

    def test_portfolio_page(self):
        """Страница портфолио доступна (200)."""
        res = self.client.get(reverse('core:portfolio'))
        self.assertEqual(res.status_code, 200)

    def test_contacts_page(self):
        """Страница контактов доступна (200)."""
        res = self.client.get(reverse('core:contacts'))
        self.assertEqual(res.status_code, 200)

    def test_cabinet_page(self):
        """Страница личного кабинета доступна (200)."""
        res = self.client.get(reverse('core:cabinet'))
        self.assertEqual(res.status_code, 200)


class SeedDemoCommandTestCase(TempMediaMixin, TestCase):
    def test_seed_populates_data(self):
        """Команда seed_demo создаёт услуги и работы с изображениями."""
        call_command('seed_demo')
        self.assertGreaterEqual(Service.objects.count(), 3)
        self.assertGreaterEqual(PortfolioItem.objects.count(), 3)
        item = PortfolioItem.objects.filter(is_published=True).first()
        self.assertGreaterEqual(item.images.filter(kind='before').count(), 1)
        self.assertGreaterEqual(item.images.filter(kind='after').count(), 2)

    def test_seed_is_idempotent(self):
        """Повторный запуск seed_demo не дублирует данные."""
        call_command('seed_demo')
        count = Service.objects.count()
        call_command('seed_demo')
        self.assertEqual(Service.objects.count(), count)

    def test_seed_flush(self):
        """Флаг --flush очищает данные перед повторным заполнением."""
        call_command('seed_demo')
        call_command('seed_demo', '--flush')
        self.assertEqual(Service.objects.count(), 6)