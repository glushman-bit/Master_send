from django.core.management.base import BaseCommand

from portfolio.models import PortfolioImage


class Command(BaseCommand):
    help = 'Создаёт эскизы (thumb) для фотографий работ, которые сохранены без них.'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for img in PortfolioImage.objects.filter(image__isnull=False):
            if img.thumb:
                skipped += 1
                continue
            img._make_thumb()
            if img.thumb:
                created += 1
            else:
                skipped += 1
        self.stdout.write(self.style.SUCCESS(f'Создано эскизов: {created}, пропущено: {skipped}.'))