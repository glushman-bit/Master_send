from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Service
        fields = '__all__'
