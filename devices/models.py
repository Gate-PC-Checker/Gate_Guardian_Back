import uuid
import io
import qrcode
from django.core.files.base import ContentFile
from django.db import models


class PC(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        STOLEN = "STOLEN", "Stolen"
        DECOMMISSIONED = "DECOMMISSIONED", "Decommissioned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    asset_tag = models.CharField(max_length=50, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)

    owner = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True,
        related_name="devices",
    )
    dpt = models.ForeignKey(
        "dpts.Department", on_delete=models.CASCADE, related_name="devices",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    qr_image = models.ImageField(upload_to="qr_codes/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.asset_tag} ({self.owner})"

    def generate_qr(self, save=True):
        """Generate a QR image encoding the qr_token and attach it to qr_image.
        Uploads to Cloudinary automatically via DEFAULT_FILE_STORAGE."""
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(str(self.qr_token))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        filename = f"{self.asset_tag}_{self.qr_token}.png"
        self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=save)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.qr_image:
            self.generate_qr(save=True)
