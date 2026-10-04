from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

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
    thumb = models.ImageField(
        upload_to='portfolio/thumbs/%Y/%m/', null=True, blank=True,
        verbose_name='Эскиз', help_text='Маленькая копия для ускорения загрузки карточек',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Фото работы'
        verbose_name_plural = 'Фото работ'
        ordering = ('order', 'id')

    def __str__(self):
        """Возвращает имя типа фото работы."""
        return f'{self.item} — {self.get_kind_display()}'

    def save(self, *args, **kwargs):
        """Сохраняет фото и создаёт рядом маленький эскиз."""
        super().save(*args, **kwargs)
        if self.image and not self.thumb:
            self._make_thumb()

    def _make_thumb(self):
        """Создаёт эскиз (JPEG, длинная сторона ~640px) для быстрого показа в карточках."""
        try:
            base_name = self.image.name.rsplit('/', 1)[-1]
            stem = base_name.rsplit('.', 1)[0]
            thumb_name = f'{stem}_thumb.jpg'

            with self.image.open('rb') as src:
                img = Image.open(src)
                img.thumbnail((640, 640), Image.LANCZOS)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                buf = BytesIO()
                img.save(buf, 'JPEG', quality=82, optimize=True)
            self.thumb.save(thumb_name, ContentFile(buf.getvalue()), save=False)
            self.__class__.objects.filter(pk=self.pk).update(thumb=self.thumb.name)
        except Exception:
            # Несчитываемое изображение — оставляем эскиз пустым (фолбэк на оригинал).
            pass
