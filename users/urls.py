from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', views.MeView.as_view(), name='me'),
    path('stats/', views.UserStatsView.as_view(), name='user_stats'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/block/', views.UserBlockView.as_view(), name='user_block'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]
