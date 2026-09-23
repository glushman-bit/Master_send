from django.db import models


class PriceTable(models.Model):
    title = models.CharField('Название таблицы', max_length=255)
    description = models.TextField('Описание', blank=True)
    cells = models.JSONField('Ячейки', default=list, blank=True)
    is_published = models.BooleanField('Опубликована', default=True)
    order = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Таблица цен'
        verbose_name_plural = 'Таблицы цен'

    def __str__(self):
        return self.title

    def normalized_cells(self):
        """Приводит все строки к одинаковой ширине."""
        rows = [[str(c) for c in row] for row in (self.cells or [])]
        if not rows:
            return [[]]
        width = max(len(row) for row in rows)
        return [row + [''] * (width - len(row)) for row in rows]