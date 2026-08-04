import logging
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from cloudinary import api as cloudinary_api
from cloudinary_storage.storage import MediaCloudinaryStorage

logger = logging.getLogger(__name__)


class CloudinaryOrLocalStorage(MediaCloudinaryStorage):
    """Try Cloudinary first, but fall back to local filesystem when Cloudinary is unavailable or rejects uploads."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fallback_storage = FileSystemStorage(
            location=str(settings.MEDIA_ROOT),
            base_url=settings.MEDIA_URL,
        )
        self._use_cloudinary = self._cloudinary_available()

    def _cloudinary_available(self):
        try:
            cloudinary_api.ping()
            return True
        except Exception:
            logger.warning("Cloudinary ping failed; using local media storage")
            return False

    def _save(self, name, content):
        if not self._use_cloudinary:
            return self._fallback_storage._save(name, content)
        try:
            return super()._save(name, content)
        except Exception:
            logger.exception("Cloudinary upload failed; falling back to local storage")
            return self._fallback_storage._save(name, content)

    def _open(self, name, mode="rb"):
        if not self._use_cloudinary:
            return self._fallback_storage._open(name, mode)
        try:
            return super()._open(name, mode)
        except Exception:
            return self._fallback_storage._open(name, mode)

    def exists(self, name):
        if not self._use_cloudinary:
            return self._fallback_storage.exists(name)
        try:
            return super().exists(name)
        except Exception:
            return self._fallback_storage.exists(name)

    def url(self, name):
        if not self._use_cloudinary:
            relative = self._fallback_storage.url(name)
            return f"{settings.PUBLIC_URL}{relative}" if settings.PUBLIC_URL else relative
        try:
            return super().url(name)
        except Exception:
            relative = self._fallback_storage.url(name)
            return f"{settings.PUBLIC_URL}{relative}" if settings.PUBLIC_URL else relative

    def delete(self, name):
        if not self._use_cloudinary:
            self._fallback_storage.delete(name)
            return
        try:
            super().delete(name)
        except Exception:
            pass
        try:
            self._fallback_storage.delete(name)
        except Exception:
            pass

    def size(self, name):
        if not self._use_cloudinary:
            return self._fallback_storage.size(name)
        try:
            return super().size(name)
        except Exception:
            return self._fallback_storage.size(name)
