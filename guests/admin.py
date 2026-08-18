from django.contrib import admin
from .models import GuestPass


@admin.register(GuestPass)
class GuestPassAdmin(admin.ModelAdmin):
    list_display = [
        "pass_id",
        "guest_name",
        "serial_number",
        "guest_id_doc",
        "guard",
        "status",
        "flagged_as_stolen",
        "checked_in_at",
        "checked_out_at",
    ]
    list_filter = ["status", "flagged_as_stolen", "checked_in_at"]
    search_fields = ["pass_id", "guest_name", "serial_number", "guest_id_doc"]
    readonly_fields = [
        "id",
        "pass_id",
        "checked_in_at",
        "checked_out_at",
        "flagged_as_stolen",
        "checkout_notes",
    ]
    ordering = ["-checked_in_at"]
