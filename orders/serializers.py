from rest_framework import serializers
from .models import OrderRequest


class OrderRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True, default=None)
    service_title = serializers.CharField(source='service.title', read_only=True, default=None)

    class Meta:
        model = OrderRequest
        fields = ('id', 'user', 'user_name', 'name', 'phone', 'email',
                  'service', 'service_title', 'message', 'status', 'status_display',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'status', 'created_at', 'updated_at')

    def validate(self, data):
        """Проверяет заявку через модель (в т.ч. запрет для мастеров)."""
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        instance = OrderRequest(**data)
        instance.user = user
        instance.full_clean()
        return data


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderRequest
        fields = ('status',)
