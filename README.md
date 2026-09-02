# Master_send

Сайт мастерской: пескоструйная обработка, порошковая покраска и сварочные работы.

## Стек

- Python 3.14, Django 6.1, Django REST Framework 3.18
- JWT-авторизация (SimpleJWT), Pillow, django-cors-headers
- SQLite (по умолчанию), Poetry

## Установка

```bash
poetry install
```

## Настройка

1. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
2. Укажите `SECRET_KEY` (обязательно):
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. Для разработки можно установить `DEBUG=True`.

## Миграции и запуск

```bash
python manage.py migrate
python manage.py runserver
```

Сайт будет доступен на http://127.0.0.1:8000, административная панель — http://127.0.0.1:8000/admin.

## Демо-данные

Заполните базу тестовыми услугами и работами портфолио (сгенерированные изображения):

```bash
python manage.py seed_demo
```

Флаг `--flush` удаляет существующие услуги и работы перед заполнением. Команда идемпотентна — повторный запуск не создаёт дубликатов.

## API

Все API находятся под префиксом `/api/`:

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/auth/register/` | Регистрация (возвращает JWT) |
| POST | `/api/auth/login/` | Вход по логину или email |
| POST | `/api/auth/refresh/` | Обновление access-токена |
| GET | `/api/auth/me/` | Текущий пользователь |
| PATCH | `/api/auth/me/` | Обновление профиля |
| POST | `/api/auth/change-password/` | Смена пароля |
| POST | `/api/auth/logout/` | Выход (blacklist refresh-токена) |
| GET | `/api/services/` | Список услуг |
| GET | `/api/portfolio/` | Работы (опубликованные) |
| GET/POST | `/api/orders/` | Заявки (создание без авторизации) |
| POST | `/api/orders/{id}/status/` | Смена статуса (только мастер) |

## Приложения

- `users` — кастомная модель пользователя, JWT-авторизация
- `services` — каталог услуг
- `portfolio` — работы «до/после»
- `orders` — заявки клиентов и управление статусами
- `core` — страницы сайта (MVT)

## Тесты

```bash
python manage.py test
```