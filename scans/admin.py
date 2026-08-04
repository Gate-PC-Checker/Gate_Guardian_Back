from django.contrib import admin
from .models import ScanLog


@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ["pc", "guard", "result", "scanned_at"]
    list_filter = ["result"]
