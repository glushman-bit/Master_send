from rest_framework import serializers
from .models import OrderRequest


class OrderRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True, default=None)

    class Meta:
        model = OrderRequest
        fields = ('id', 'user', 'user_name', 'name', 'phone', 'email',
                  'service', 'message', 'status', 'status_display',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'status', 'created_at', 'updated_at')


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderRequest
        fields = ('status',)
