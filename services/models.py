from django.db import models


class Service(models.Model):
    class Category(models.TextChoices):
        SAND = 'sand', 'Пескоструй'
        POWDER = 'powder', 'Порошковая покраска'
        WELD = 'weld', 'Сварка'

    category = models.CharField(max_length=10, choices=Category.choices, verbose_name='Категория')
    title = models.CharField(max_length=150, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    price_from = models.PositiveIntegerField(verbose_name='Цена от, ₽')
    price_unit = models.CharField(max_length=50, default='за м²', verbose_name='Единица измерения')
    icon = models.CharField(max_length=10, default='⚙', verbose_name='Иконка (emoji)')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ('order', 'id')

    def __str__(self):
        return f'{self.get_category_display()} — {self.title}'
