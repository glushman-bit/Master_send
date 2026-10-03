from django.urls import include, path
from rest_framework.routers import DefaultRouter

from prices.views import PricePublicViewSet

public_router = DefaultRouter()
public_router.register('', PricePublicViewSet, basename='price')

urlpatterns = [
    path('', include(public_router.urls)),
]
