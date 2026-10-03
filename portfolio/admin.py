from django.contrib import admin

from .models import PortfolioItem


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'service', 'is_published', 'created_at')
    list_filter = ('is_published', 'service', 'created_at')
    search_fields = ('title', 'description')
