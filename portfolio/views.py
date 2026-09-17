import json

from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from .models import PortfolioItem, PortfolioImage
from .serializers import PortfolioItemSerializer
from core.permissions import IsMaster


class PortfolioViewSet(viewsets.ReadOnlyModelViewSet):
    """Список и детали опубликованных работ портфолио (read-only для всех)."""
    queryset = PortfolioItem.objects.filter(is_published=True)
    serializer_class = PortfolioItemSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        """Возвращает опубликованные работы, при необходимости фильтруя по услуге."""
        qs = super().get_queryset()
        service = self.request.query_params.get('service')
        if service:
            qs = qs.filter(service_id=service)
        return qs


class PortfolioAdminViewSet(viewsets.ModelViewSet):
    """
    Управление работами портфолио (только для мастеров/администраторов):
    создание, просмотр всех (в т.ч. скрытых), изменение, удаление.
    """
    queryset = PortfolioItem.objects.all()
    serializer_class = PortfolioItemSerializer
    permission_classes = (IsMaster,)

    def _apply_images(self, instance, request):
        """Добавляет новые фото из form-data и удаляет отмеченные."""
        removed = request.data.get('remove_images')
        if removed:
            try:
                ids = json.loads(removed)
            except (TypeError, ValueError):
                ids = []
            for pk in ids or []:
                img = instance.images.filter(pk=pk).first()
                if img:
                    if img.image and img.image.name:
                        img.image.storage.delete(img.image.name)
                    img.delete()

        next_order = {
            kind: (instance.images.filter(kind=kind).aggregate(m=models.Max('order'))['m'] or -1) + 1
            for kind in PortfolioImage.Kind.values
        }
        for kind in PortfolioImage.Kind.values:
            for i, upload in enumerate(request.FILES.getlist(f'images_{kind}') or []):
                instance.images.create(kind=kind, image=upload, order=next_order[kind] + i)

    def create(self, request, *args, **kwargs):
        """Создаёт работу и прикрепляет несколько фото «до»/«после»."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self._apply_images(instance, request)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Обновляет работу и изменяет набор фото «до»/«после»."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        self._apply_images(instance, request)
        return Response(self.get_serializer(instance).data)

    def perform_destroy(self, instance):
        """Удаляет запись и все файлы изображений с диска."""
        for img in instance.images.all():
            if img.image and img.image.name:
                img.image.storage.delete(img.image.name)
        instance.delete()
