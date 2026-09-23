from django.db import models
from services.models import Service


class PortfolioItem(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='portfolio', verbose_name='Услуга')
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Работа'
        verbose_name_plural = 'Работы'
        ordering = ('created_at',)

    def __str__(self):
        """Возвращает название работы."""
        return self.title


class PortfolioImage(models.Model):
    """Фотография работы «до» или «после» (у работы может быть несколько фото)."""

    class Kind(models.TextChoices):
        BEFORE = 'before', 'До'
        AFTER = 'after', 'После'

    item = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name='images', verbose_name='Работа')
    kind = models.CharField(max_length=10, choices=Kind.choices, verbose_name='Тип фото')
    image = models.ImageField(upload_to='portfolio/%Y/%m/', verbose_name='Фото')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Фото работы'
        verbose_name_plural = 'Фото работ'
        ordering = ('order', 'id')

    def __str__(self):
        """Возвращает имя типа фото работы."""
        return f'{self.item} — {self.get_kind_display()}'
