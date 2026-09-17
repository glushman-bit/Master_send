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
    def _apply_images(page, request):
        """Добавляет новые фото из form-data и удаляет отмеченные."""
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

        next_order = (page.images.aggregate(m=models.Max('order'))['m'] or -1)
        for i, upload in enumerate(request.FILES.getlist('images')):
            page.images.create(image=upload, order=next_order + 1 + i)

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