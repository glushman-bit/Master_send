from rest_framework import viewsets, permissions
from .models import PortfolioItem
from .serializers import PortfolioItemSerializer


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
