import json

from django.db import models
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsMaster

from .models import AboutPage
from .serializers import AboutPageSerializer


class AboutView(APIView):
    """Публичное API: последняя опубликованная страница «О нас»."""

    permission_classes = ()

    def get(self, request):
        """Возвращает содержание страницы «О нас»."""
        page = AboutPage.objects.filter(is_published=True).first()
        if page is None:
            return Response({'description': '', 'images': [], 'is_published': True})
        return Response(AboutPageSerializer(page).data)


class AdminAboutView(APIView):
    """Управление страницей «О нас» (только для мастеров/администраторов)."""

    permission_classes = (IsMaster,)

    @staticmethod
    def _get_or_create():
        """Возвращает последнюю страницу, создавая пустую при необходимости."""
        page = AboutPage.objects.order_by('-updated_at').first()
        if page is None:
            page = AboutPage.objects.create(description='')
        return page

    @staticmethod
    def _apply_meta(img, entry):
        """Применяет к фото размер и центрование с проверкой значений."""
        if not isinstance(entry, dict):
            return
        scale = entry.get('scale')
        if isinstance(scale, int) and 20 <= scale <= 300:
            img.scale = scale
        if entry.get('pos_x') in ('left', 'center', 'right'):
            img.pos_x = entry['pos_x']
        if entry.get('pos_y') in ('top', 'center', 'bottom'):
            img.pos_y = entry['pos_y']
        img.save(update_fields=['scale', 'pos_x', 'pos_y'])

    @staticmethod
    def _apply_images(page, request):
        """Добавляет новые фото, обновляет размеры/центрование и удаляет отмеченные."""
        removed = request.data.get('remove_images')
        if removed:
            try:
                ids = json.loads(removed)
            except (TypeError, ValueError):
                ids = []
            for pk in ids or []:
                img = page.images.filter(pk=pk).first()
                if img:
                    if img.image and img.image.name:
                        img.image.storage.delete(img.image.name)
                    img.delete()

        meta = request.data.get('images_meta')
        if meta:
            try:
                meta = json.loads(meta)
            except (TypeError, ValueError):
                meta = []
            for entry in meta or []:
                pk = entry.get('id') if isinstance(entry, dict) else None
                if not pk:
                    continue
                img = page.images.filter(pk=pk).first()
                if img:
                    AdminAboutView._apply_meta(img, entry)

        next_order = page.images.aggregate(m=models.Max('order'))['m'] or -1
        created = []
        for i, upload in enumerate(request.FILES.getlist('images')):
            created.append(page.images.create(image=upload, order=next_order + 1 + i))

        new_meta = request.data.get('images_new_meta')
        if new_meta:
            try:
                new_meta = json.loads(new_meta)
            except (TypeError, ValueError):
                new_meta = []
            for img, entry in zip(created, new_meta or []):
                AdminAboutView._apply_meta(img, entry)

    def get(self, request):
        """Возвращает редактируемую страницу «О нас»."""
        return Response(AboutPageSerializer(self._get_or_create()).data)

    def put(self, request):
        """Обновляет описание и набор фотографий страницы «О нас»."""
        page = self._get_or_create()
        serializer = AboutPageSerializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        page = serializer.save()
        self._apply_images(page, request)
        return Response(AboutPageSerializer(page).data, status=status.HTTP_200_OK)
