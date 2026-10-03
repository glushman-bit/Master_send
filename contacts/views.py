from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsMaster

from .models import ContactPage
from .serializers import ContactPageSerializer


def _no_store(response):
    """Отключает кэширование ответа, чтобы сайт не показывал устаревшие данные."""
    response['Cache-Control'] = 'no-store'
    return response


class ContactView(APIView):
    """Публичное API: последняя опубликованная контактная информация."""

    permission_classes = ()

    def get(self, request):
        """Возвращает контактную информацию."""
        page = ContactPage.objects.filter(is_published=True).first()
        if page is None:
            return _no_store(
                Response(
                    {
                        'phone': '',
                        'email': '',
                        'address': '',
                        'work_hours': '',
                        'is_published': True,
                    }
                )
            )
        return _no_store(Response(ContactPageSerializer(page).data))


class AdminContactView(APIView):
    """Управление контактной информацией (только для мастеров/администраторов)."""

    permission_classes = (IsMaster,)

    @staticmethod
    def _get_or_create():
        """Возвращает последнюю запись, создавая пустую при необходимости."""
        page = ContactPage.objects.order_by('-updated_at').first()
        if page is None:
            page = ContactPage.objects.create()
        return page

    def get(self, request):
        """Возвращает редактируемую контактную информацию."""
        return _no_store(Response(ContactPageSerializer(self._get_or_create()).data))

    def put(self, request):
        """Обновляет контактную информацию."""
        page = self._get_or_create()
        serializer = ContactPageSerializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        page = serializer.save()
        return _no_store(Response(ContactPageSerializer(page).data, status=status.HTTP_200_OK))
