from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'portfolio'
router = DefaultRouter()
router.register('', views.PortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('', include(router.urls)),
]
