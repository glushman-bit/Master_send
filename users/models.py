from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'client', 'Клиент'
        MASTER = 'master', 'Мастер'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CLIENT, verbose_name='Роль')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True, verbose_name='Аватар')
    bio = models.TextField(blank=True, max_length=500, verbose_name='О себе')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_master(self):
        return self.role == self.Role.MASTER or self.is_superuser

    @property
    def initials(self):
        name = self.get_full_name() or self.username
        return ''.join(p[0] for p in name.split()[:2]).upper()
