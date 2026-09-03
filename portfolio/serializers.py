from rest_framework import serializers
from .models import PortfolioItem


class PortfolioItemSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source='service.title', read_only=True)

    class Meta:
        model = PortfolioItem
        fields = ('id', 'service', 'service_title', 'title', 'description',
                  'image_before', 'image_after', 'created_at')
