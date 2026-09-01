from django.conf import settings
from django.db import models
from services.models import Service


class OrderRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'progress', 'В работе'
        DONE = 'done', 'Выполнена'
        CANCELLED = 'cancelled', 'Отменена'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='orders', verbose_name='Клиент',
    )
    name = models.CharField(max_length=100, verbose_name='Имя')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, verbose_name='Услуга')
    message = models.TextField(verbose_name='Описание задачи')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.name} — {self.service or "без услуги"}'
