from django.db import models


class ContactPage(models.Model):
    """Контактная информация (на сайте показывается последняя опубликованная)."""

    phone = models.CharField(max_length=50, blank=True, default='', verbose_name='Телефон')
    email = models.EmailField(max_length=254, blank=True, default='', verbose_name='Email')
    address = models.CharField(max_length=300, blank=True, default='', verbose_name='Адрес')
    work_hours = models.CharField(max_length=200, blank=True, default='', verbose_name='Режим работы')
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Контакты'
        verbose_name_plural = 'Контакты'
        ordering = ('-updated_at',)

    def __str__(self):
        return self.phone or 'Контакты'
