from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from portfolio.views import PortfolioAdminViewSet
from services.views import ServiceAdminViewSet


admin_router = DefaultRouter()
admin_router.register('portfolio', PortfolioAdminViewSet, basename='admin-portfolio')
admin_router.register('services', ServiceAdminViewSet, basename='admin-services')


urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/auth/', include('users.urls')),
    path('api/services/', include('services.urls')),
    path('api/portfolio/', include('portfolio.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/admin/', include(admin_router.urls)),

    # Страницы
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
