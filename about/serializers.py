from rest_framework import serializers
from .models import AboutPage, AboutImage


class AboutImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutImage
        fields = ('id', 'image', 'order')


class AboutPageSerializer(serializers.ModelSerializer):
    images = AboutImageSerializer(many=True, read_only=True)

    class Meta:
        model = AboutPage
        fields = ('id', 'description', 'images', 'is_published', 'created_at', 'updated_at')