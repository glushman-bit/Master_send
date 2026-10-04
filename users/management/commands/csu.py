import os

from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    """Создание (или обновление) суперпользователя.

    Логин/пароль берутся из переменных окружения ADMIN_USERNAME и ADMIN_PASSWORD.
    Если пароль не задан, используется значение по умолчанию 'admin'.
    """

    help = 'Создаёт суперпользователя из ADMIN_USERNAME / ADMIN_PASSWORD (по умолчанию admin/admin).'

    def handle(self, *args, **options):
        """Создаёт или обновляет суперпользователя из переменных окружения."""
        username = os.getenv('ADMIN_USERNAME', 'admin').strip()
        email = os.getenv('ADMIN_EMAIL', 'admin@example.com').strip()
        password = os.getenv('ADMIN_PASSWORD', 'admin')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email},
        )
        user.email = email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.email_verified = True
        user.set_password(password)
        user.save()

        verb = 'создан' if created else 'обновлён'
        self.stdout.write(
            self.style.SUCCESS(f'Суперпользователь "{username}" {verb}. Логин: {username}, пароль: {password}.')
        )
