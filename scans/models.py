import uuid
from django.db import models


class ScanLog(models.Model):
    class Result(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        DENIED = "DENIED", "Denied"
        STOLEN_FLAG = "STOLEN_FLAG", "Stolen device flagged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pc = models.ForeignKey("devices.PC", on_delete=models.CASCADE, related_name="scan_logs")
    guard = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="scans_performed")

    result = models.CharField(max_length=20, choices=Result.choices)
    photo_evidence = models.ImageField(upload_to="scan_evidence/", blank=True, null=True)
    notes = models.CharField(max_length=255, blank=True)

    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"{self.pc.asset_tag} - {self.result} @ {self.scanned_at}"
