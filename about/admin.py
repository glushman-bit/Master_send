from django.contrib import admin

from .models import AboutImage, AboutPage


class AboutImageInline(admin.TabularInline):
    model = AboutImage
    extra = 1


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ('description', 'is_published', 'updated_at')
    inlines = (AboutImageInline,)
