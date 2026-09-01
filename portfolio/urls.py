from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'portfolio'
router = DefaultRouter()
router.register('', views.PortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('', include(router.urls)),
]
