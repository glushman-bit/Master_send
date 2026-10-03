from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'services'
router = DefaultRouter()
router.register('', views.ServiceViewSet, basename='service')

urlpatterns = [
    path('', include(router.urls)),
]
