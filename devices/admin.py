from django.contrib import admin
from .models import PC


@admin.register(PC)
class PCAdmin(admin.ModelAdmin):
    list_display = ["asset_tag", "owner", "dpt", "status", "created_at"]
    list_filter = ["status", "dpt"]
    search_fields = ["asset_tag", "serial_number", "owner__username"]
