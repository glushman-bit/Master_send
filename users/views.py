from datetime import timedelta

from django.contrib.auth import get_user_model, login, logout
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
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import get_verification_user_id, send_verification_email

User = get_user_model()


def get_tokens_for_user(user):
    """Возвращает пару JWT-токенов (refresh и access) для пользователя."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class RegisterView(generics.CreateAPIView):
    """Регистрация — создаёт аккаунт и отправляет письмо для подтверждения email."""

    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'register'
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        """Создаёт пользователя (email не подтверждён) и шлёт письмо со ссылкой."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.email_verified = False
        user.save(update_fields=['email_verified'])
        send_verification_email(user)
        # Аккаунт недоступен до подтверждения email: токены не выдаём и сессию не создаём.
        return Response(
            {
                'detail': 'Мы отправили письмо для подтверждения email. '
                          'Перейдите по ссылке из письма, чтобы активировать аккаунт.',
                'email': user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class ResendVerificationView(APIView):
    """Повторная отправка письма подтверждения по email."""

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'resend_verification'

    def post(self, request):
        """Отправляет письмо, если пользователь с таким email существует и ещё не подтверждён."""
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'detail': 'Укажите email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(email__iexact=email).first()
        if user and user.email_verified is False:
            send_verification_email(user)
        # Всегда отвечаем одинаково, чтобы не раскрывать, зарегистрирован ли email.
        return Response({'detail': 'Если такой email зарегистрирован и не подтверждён, письмо отправлено.'})


class VerifyEmailView(APIView):
    """Подтверждение email по токену из письма — активирует аккаунт и выдаёт токены."""

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'verify_email'

    def post(self, request):
        """Проверяет токен, подтверждает email и авторизует пользователя."""
        token = (request.data.get('token') or '').strip()
        user_id = get_verification_user_id(token)
        user = None
        if user_id:
            user = User.objects.filter(pk=user_id).first()

        if not user:
            return Response(
                {'detail': 'Ссылка недействительна или истекла. Запросите новое письмо.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {'detail': 'Аккаунт заблокирован. Обратитесь к администратору.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        # Сессия нужна серверным guard-страницам (админ-панель, кабинет).
        login(request, user)
        tokens = get_tokens_for_user(user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'tokens': tokens,
            }
        )


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
        if not user or not user.is_active:
            return Response(
                {'detail': 'Неверный логин или пароль.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.check_password(password):
            return Response(
                {'detail': 'Неверный логин или пароль.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Email не подтверждён — вход запрещён, но даём пользователю понятное сообщение.
        if not user.email_verified:
            return Response(
                {
                    'detail': 'Подтвердите адрес электронной почты. Перейдите по ссылке из письма.',
                    'code': 'email_not_verified',
                    'email': user.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        tokens = get_tokens_for_user(user)
        # Создаём Django-сессию, чтобы серверные guard-страницы (админ-панель) видели пользователя.
        login(request, user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'tokens': tokens,
            }
        )


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
        """Отзывает (blacklist) refresh-токен пользователя при выходе и завершает сессию."""
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'detail': 'Нет refresh токена.'}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            logout(request)
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

        return Response(
            {
                'total': total,
                'clients': clients,
                'masters': masters,
                'new_month': new_month,
                'active_week': active_week,
            }
        )


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
            result.append(
                {
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
                    'is_active': u.is_active,
                    'is_superuser': u.is_superuser,
                    'orders': {
                        'total': u.orders_total,
                        'new': u.orders_new,
                        'progress': u.orders_progress,
                        'done': u.orders_done,
                        'cancelled': u.orders_cancelled,
                    },
                }
            )

        return Response(result)


class UserBlockView(APIView):
    """Блокировка/разблокировка пользователя (только для мастеров)."""

    permission_classes = (IsMaster,)

    def post(self, request, pk=None):
        """Меняет статус is_active пользователя. Суперпользователей и себя блокировать нельзя."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Пользователь не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_active = bool(request.data.get('is_active', False))

        if user.is_superuser:
            return Response(
                {'detail': 'Нельзя заблокировать администратора.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.pk == request.user.pk:
            return Response(
                {'detail': 'Нельзя изменить статус собственного аккаунта.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_active != is_active:
            user.is_active = is_active
            user.save(update_fields=['is_active'])

        return Response(
            {
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active,
                'detail': 'Пользователь заблокирован.' if not is_active else 'Пользователь разблокирован.',
            }
        )
