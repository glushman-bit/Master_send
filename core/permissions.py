from rest_framework import permissions


class IsMaster(permissions.BasePermission):
    """Разрешает доступ только авторизованным мастерам и администраторам."""

    message = 'Доступно только мастерам и администраторам.'

    def has_permission(self, request, view):
        """Возвращает True только для авторизованного мастера/суперпользователя."""
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and user.is_master)


class IsNotMaster(permissions.BasePermission):
    """Запрещает действие мастерам и администраторам."""

    message = 'Мастер не может оставлять заявки на работу.'

    def has_permission(self, request, view):
        """Гостям разрешает, мастерам/администраторам — запрещает."""
        if not request.user.is_authenticated:
            return True
        return not request.user.is_master