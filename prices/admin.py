from django.contrib import admin

from prices.models import PriceTable


@admin.register(PriceTable)
class PriceTableAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_published', 'updated_at')
    list_editable = ('order', 'is_published')
    search_fields = ('title', 'description')
