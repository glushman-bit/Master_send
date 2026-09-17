from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import IsMaster
from orders.models import OrderRequest
from .serializers import (
    UserSerializer, RegisterSerializer,
    ChangePasswordSerializer, ProfileUpdateSerializer,
)

User = get_user_model()


def get_tokens_for_user(user):
    """Возвращает пару JWT-токенов (refresh и access) для пользователя."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class RegisterView(generics.CreateAPIView):
    """Регистрация — возвращает JWT-токены."""
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'register'
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        """Регистрирует нового пользователя и возвращает его данные и JWT-токены."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Вход по username/email + password."""
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'login'

    def post(self, request):
        """Выполняет вход и возвращает JWT-токены для аутентифицированного пользователя."""
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'detail': 'Введите логин и пароль.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ищем по username или email
        user = None
        if '@' in username:
            user = User.objects.filter(email__iexact=username).first()
        else:
            user = User.objects.filter(username__iexact=username).first()

        # Пароль неверный ИЛИ аккаунт деактивирован — одинаковый ответ (не раскрываем деталей).
        if not user or not user.is_active or not user.check_password(password):
            return Response(
                {'detail': 'Неверный логин или пароль.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })


class MeView(generics.RetrieveUpdateAPIView):
    """Текущий пользователь (GET — получить, PUT/PATCH — обновить)."""
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        """Для изменений возвращает сериализатор обновления профиля, иначе — чтения."""
        if self.request.method in ('PUT', 'PATCH'):
            return ProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        """Возвращает текущего авторизованного пользователя."""
        return self.request.user


class ChangePasswordView(APIView):
    """Смена пароля."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """Меняет пароль текущего пользователя."""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Пароль изменён.'})


class LogoutView(APIView):
    """Отзыв refresh-токена."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """Отзывает (blacklist) refresh-токен пользователя при выходе."""
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'detail': 'Нет refresh токена.'}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Вы вышли из системы.'})
        except Exception:
            return Response({'detail': 'Невалидный токен.'}, status=status.HTTP_400_BAD_REQUEST)


class UserStatsView(APIView):
    """Статистика пользователей для панели администратора (только для мастеров)."""
    permission_classes = (IsMaster,)

    def get(self, request):
        """Возвращает сводную статистику по пользователям для панели администратора."""
        now = timezone.now()
        month_ago = now - timedelta(days=30)

        total = User.objects.count()
        clients = User.objects.filter(role='client').count()
        masters = User.objects.filter(Q(role='master') | Q(is_superuser=True)).count()
        new_month = User.objects.filter(date_joined__gte=month_ago).count()
        active_week = User.objects.filter(last_login__gte=now - timedelta(days=7)).count()

        return Response({
            'total': total,
            'clients': clients,
            'masters': masters,
            'new_month': new_month,
            'active_week': active_week,
        })


class UserListView(APIView):
    """Список пользователей с количеством заказов по статусам (только для мастеров)."""
    permission_classes = (IsMaster,)

    def get(self, request):
        """Возвращает список пользователей с количеством заказов по статусам."""
        users = User.objects.annotate(
            orders_total=Count('orders'),
            orders_new=Count('orders', filter=Q(orders__status=OrderRequest.Status.NEW)),
            orders_progress=Count('orders', filter=Q(orders__status=OrderRequest.Status.IN_PROGRESS)),
            orders_done=Count('orders', filter=Q(orders__status=OrderRequest.Status.DONE)),
            orders_cancelled=Count('orders', filter=Q(orders__status=OrderRequest.Status.CANCELLED)),
        ).order_by('-date_joined')

        result = []
        for u in users:
            result.append({
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'email': u.email,
                'phone': u.phone,
                'avatar': u.avatar.url if u.avatar else None,
                'role': u.role,
                'initials': u.initials,
                'date_joined': u.date_joined,
                'is_master': u.is_master,
                'orders': {
                    'total': u.orders_total,
                    'new': u.orders_new,
                    'progress': u.orders_progress,
                    'done': u.orders_done,
                    'cancelled': u.orders_cancelled,
                },
            })

        return Response(result)
