import logging
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from cloudinary_storage.storage import MediaCloudinaryStorage

logger = logging.getLogger(__name__)


class CloudinaryOrLocalStorage(MediaCloudinaryStorage):
    """Try Cloudinary first, but fall back to local filesystem if Cloudinary rejects the upload."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fallback_storage = FileSystemStorage(
            location=str(settings.MEDIA_ROOT),
            base_url=settings.MEDIA_URL,
        )

    def _save(self, name, content):
        try:
            return super()._save(name, content)
        except Exception:
            logger.exception("Cloudinary upload failed; falling back to local storage")
            return self._fallback_storage._save(name, content)

    def _open(self, name, mode="rb"):
        try:
            return super()._open(name, mode)
        except Exception:
            return self._fallback_storage._open(name, mode)

    def exists(self, name):
        try:
            return super().exists(name)
        except Exception:
            return self._fallback_storage.exists(name)

    def url(self, name):
        try:
            return super().url(name)
        except Exception:
            return self._fallback_storage.url(name)

    def delete(self, name):
        try:
            super().delete(name)
        except Exception:
            pass
        try:
            self._fallback_storage.delete(name)
        except Exception:
            pass

    def size(self, name):
        try:
            return super().size(name)
        except Exception:
            return self._fallback_storage.size(name)
