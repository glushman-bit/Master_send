from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsMaster, IsNotMaster

from .models import OrderRequest
from .serializers import OrderRequestSerializer, OrderStatusUpdateSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """
    - Клиент: может создавать заявку и видит только свои.
    - Мастер: видит все заявки и может менять статус, но не может создавать.
    """

    serializer_class = OrderRequestSerializer

    def get_permissions(self):
        """Возвращает набор разрешений в зависимости от выполняемого действия."""
        if self.action in ('create',):
            return [permissions.IsAuthenticated(), IsNotMaster()]
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy', 'update_status', 'stats'):
            return [IsMaster()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Возвращает заявки: мастер видит все, клиент — только свои."""
        user = self.request.user
        if not user.is_authenticated:
            return OrderRequest.objects.none()
        if user.is_master:
            qs = OrderRequest.objects.all()
        else:
            qs = OrderRequest.objects.filter(user=user)
        status = self.request.query_params.get('status')
        if status in OrderRequest.Status.values:
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        """Сохраняет заявку, привязывая текущего авторизованного пользователя, и шлёт уведомление."""
        user = self.request.user if self.request.user.is_authenticated else None
        order = serializer.save(user=user)
        self._notify(order)

    @staticmethod
    def _notify(order):
        """Отправляет письмо приёмщику мастерской о новой заявке (в dev — в консоль)."""
        try:
            subject = f'Новая заявка: {order.name}'
            service_title = order.service.title if order.service else 'без услуги'
            body = (
                f'Имя: {order.name}\n'
                f'Телефон: {order.phone}\n'
                f'Email: {order.email or "—"}\n'
                f'Услуга: {service_title}\n'
                f'Задача:\n{order.message}\n'
            )
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ORDER_NOTIFY_RECIPIENTS],
                fail_silently=True,
            )
        except Exception:
            # Письмо не должно ломать создание заявки.
            pass

    @action(detail=True, methods=['post'], url_path='status')
    def update_status(self, request, pk=None):
        """Обновляет статус заявки (доступно мастерам)."""
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrderRequestSerializer(order).data)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Сводка по заявкам для панели администратора."""
        counts = {c['status']: c['n'] for c in OrderRequest.objects.values('status').annotate(n=Count('id'))}
        data = {
            'new': counts.get(OrderRequest.Status.NEW, 0),
            'in_progress': counts.get(OrderRequest.Status.IN_PROGRESS, 0),
            'done': counts.get(OrderRequest.Status.DONE, 0),
            'cancelled': counts.get(OrderRequest.Status.CANCELLED, 0),
            'total': OrderRequest.objects.count(),
        }
        return Response(data)
