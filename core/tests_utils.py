import shutil
import tempfile

from django.test import override_settings


class TempMediaMixin:
    """Перенаправляет MEDIA_ROOT во временную папку и изолирует кэш на время теста."""

    def setUp(self):
        """Перенаправляет MEDIA_ROOT и переключает кэш в LocMemCache."""
        self._tmp_media = None
        self._tmp_media = tempfile.mkdtemp()
        self.override = override_settings(
            MEDIA_ROOT=self._tmp_media,
            CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
        )
        self.override.enable()
        from django.core.cache import cache
        cache.clear()
        super().setUp()

    def tearDown(self):
        """Отключает переопределение MEDIA_ROOT и удаляет временную папку."""
        if getattr(self, 'override', None) is not None:
            self.override.disable()
        super().tearDown()
        if self._tmp_media:
            shutil.rmtree(self._tmp_media, ignore_errors=True)
