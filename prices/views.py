from rest_framework import permissions, viewsets

from core.permissions import IsMaster
from prices.models import PriceTable
from prices.serializers import (
    PriceTableAdminSerializer,
    PriceTableSerializer,
)


class PricePublicViewSet(viewsets.ReadOnlyModelViewSet):
    """Публичный список таблиц цен (только опубликованные)."""
    queryset = PriceTable.objects.filter(is_published=True)
    serializer_class = PriceTableSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class AdminPriceViewSet(viewsets.ModelViewSet):
    """Редактирование таблиц цен из панели администратора."""
    queryset = PriceTable.objects.all()
    serializer_class = PriceTableAdminSerializer
    permission_classes = (IsMaster,)
    pagination_class = None
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']