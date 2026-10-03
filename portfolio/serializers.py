from rest_framework import serializers

from .models import PortfolioImage, PortfolioItem


class PortfolioImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioImage
        fields = ('id', 'kind', 'image', 'order')


class PortfolioItemSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source='service.title', read_only=True)
    images = PortfolioImageSerializer(many=True, read_only=True)

    class Meta:
        model = PortfolioItem
        fields = ('id', 'service', 'service_title', 'title', 'description', 'images', 'is_published', 'created_at')
