from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('services/', views.services_view, name='services'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('about/', views.about_view, name='about'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('cabinet/', views.cabinet_view, name='cabinet'),
    path('verify/', views.verify_email_page, name='verify_email_page'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
]
