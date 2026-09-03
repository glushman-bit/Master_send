from rest_framework import viewsets, permissions
from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Список и детали услуг (read-only для всех)."""
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        """Возвращает активные услуги, при необходимости фильтруя по категории."""
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs
