"""Аутентификация на базе JWT с проверкой активности пользователя."""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class ActiveUserJWTAuthentication(JWTAuthentication):
    """Rejects tokens of blocked (is_active=False) users on every request."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user and not user.is_active:
            raise AuthenticationFailed(
                'Аккаунт заблокирован. Обратитесь к администратору.',
                code='user_inactive',
            )
        return user
