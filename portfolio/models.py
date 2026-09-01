from django.db import models
from services.models import Service


class PortfolioItem(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='portfolio', verbose_name='Услуга')
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    image_before = models.ImageField(upload_to='portfolio/before/%Y/%m/', blank=True, verbose_name='До')
    image_after = models.ImageField(upload_to='portfolio/after/%Y/%m/', verbose_name='После')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Работа'
        verbose_name_plural = 'Работы'
        ordering = ('-created_at',)

    def __str__(self):
        return self.title
