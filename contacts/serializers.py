from rest_framework import serializers

from .models import ContactPage


class ContactPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPage
        fields = ('id', 'phone', 'email', 'address', 'work_hours', 'is_published', 'created_at', 'updated_at')
