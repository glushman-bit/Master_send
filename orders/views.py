from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import OrderRequest
from .serializers import OrderRequestSerializer, OrderStatusUpdateSerializer


class IsMaster(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_master


class OrderViewSet(viewsets.ModelViewSet):
    """
    - Клиент: видит только свои заявки.
    - Мастер: видит все заявки и может менять статус.
    """
    serializer_class = OrderRequestSerializer

    def get_permissions(self):
        if self.action in ('create',):
            return [permissions.AllowAny()]
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        if self.action in ('update_status',):
            return [IsMaster()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return OrderRequest.objects.none()
        if user.is_master:
            return OrderRequest.objects.all()
        return OrderRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

    @action(detail=True, methods=['post'], url_path='status')
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrderRequestSerializer(order).data)
