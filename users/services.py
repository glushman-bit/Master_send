"""Служебные функции подтверждения email (токены + письма)."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

logger = logging.getLogger(__name__)

VERIFY_SALT = 'email-verify'
# Срок жизни ссылки подтверждения (часов).
VERIFY_TOKEN_MAX_AGE = 48 * 3600

_verifier = TimestampSigner(salt=VERIFY_SALT)


def make_verification_token(user):
    """Возвращает подписанный токен подтверждения для пользователя."""
    return _verifier.sign(str(user.pk))


def get_verification_user_id(token):
    """Возвращает id пользователя по валидному токену либо None (просрочен/невалиден)."""
    try:
        return int(_verifier.unsign(token, max_age=VERIFY_TOKEN_MAX_AGE))
    except (BadSignature, SignatureExpired, ValueError):
        return None


def build_verification_url(user):
    """Формирует полную ссылку подтверждения для письма."""
    return f"{settings.SITE_URL}/verify/?token={make_verification_token(user)}"


def send_verification_email(user):
    """Отправляет письмо со ссылкой подтверждения (по SMTP или в консоль в dev)."""
    link = build_verification_url(user)
    subject = 'Подтвердите регистрацию на MasterBlast'
    text = (
        f'Здравствуйте, {user.get_full_name() or user.username}!\n\n'
        f'Вы зарегистрировались на сайте MasterBlast. '
        f'Чтобы активировать аккаунт, подтвердите адрес электронной почты:\n'
        f'{link}\n\n'
        f'Если вы не регистрировались, просто проигнорируйте это письмо.\n'
        f'Ссылка действительна в течение 48 часов.'
    )
    html = (
        f'<p>Здравствуйте, <b>{user.get_full_name() or user.username}</b>!</p>'
        f'<p>Вы зарегистрировались на сайте MasterBlast. Чтобы активировать аккаунт, '
        f'подтвердите адрес электронной почты:</p>'
        f'<p><a href="{link}" style="display:inline-block;padding:12px 24px;background:#e69f25;color:#fff;'
        f'border-radius:4px;text-decoration:none;font-weight:bold;">Подтвердить email</a></p>'
        f'<p style="color:#666;font-size:13px;">Если кнопка не работает, скопируйте ссылку в браузер: '
        f'<a href="{link}">{link}</a></p>'
        f'<p style="color:#666;font-size:13px;">Ссылка действительна в течение 48 часов. '
        f'Если вы не регистрировались, просто проигнорируйте это письмо.</p>'
    )
    try:
        send_mail(
            subject,
            text,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html,
            fail_silently=True,
        )
    except Exception:
        logger.exception('Не удалось отправить письмо подтверждения для пользователя %s (%s)', user.pk, user.email)