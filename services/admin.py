from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price_from', 'is_active', 'order')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'description')
