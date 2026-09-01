from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('services/', views.services_view, name='services'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('cabinet/', views.cabinet_view, name='cabinet'),
]
