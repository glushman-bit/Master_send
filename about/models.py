from django.db import models


class AboutPage(models.Model):
    """Текст страницы «О нас» (на сайте используется последняя опубликованная)."""
    description = models.TextField(verbose_name='Описание')
    is_published = models.BooleanField(default=True, verbose_name='Опубликована')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Страница «О нас»'
        verbose_name_plural = 'Страницы «О нас»'
        ordering = ('-updated_at',)

    def __str__(self):
        """Возвращает краткое описание страницы."""
        return self.description[:50]


class AboutImage(models.Model):
    """Фотография для страницы «О нас»."""

    class PositionX(models.TextChoices):
        LEFT = 'left', 'Слева'
        CENTER = 'center', 'По центру'
        RIGHT = 'right', 'Справа'

    class PositionY(models.TextChoices):
        TOP = 'top', 'Сверху'
        CENTER = 'center', 'По центру'
        BOTTOM = 'bottom', 'Снизу'

    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name='images', verbose_name='Страница')
    image = models.ImageField(upload_to='about/%Y/%m/', verbose_name='Фото')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    scale = models.PositiveIntegerField(default=100, verbose_name='Размер, %')
    pos_x = models.CharField(max_length=10, choices=PositionX.choices, default=PositionX.CENTER, verbose_name='Центрование по горизонтали')
    pos_y = models.CharField(max_length=10, choices=PositionY.choices, default=PositionY.CENTER, verbose_name='Центрование по вертикали')

    class Meta:
        verbose_name = 'Фото страницы «О нас»'
        verbose_name_plural = 'Фото страницы «О нас»'
        ordering = ('order', 'id')

    def __str__(self):
        """Возвращает имя файла фото."""
        return str(self.image.name)