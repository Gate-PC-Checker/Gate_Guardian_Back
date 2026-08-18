from accounts.serializers import serialize_image_value
from rest_framework import serializers
from .models import GuestPass


class GuestPassCreateSerializer(serializers.ModelSerializer):
    """Used by guard to check in a guest with ID photo and device serial number."""

    class Meta:
        model = GuestPass
        fields = ["guest_name", "guest_id_doc", "serial_number", "id_photo"]

    def validate_serial_number(self, value):
        return value.strip() if value else ""


class GuestPassSerializer(serializers.ModelSerializer):
    """Full read serializer for lookup and listing."""
    guard_username = serializers.CharField(source="guard.username", read_only=True)
    guard_name = serializers.SerializerMethodField()
    id_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = GuestPass
        fields = [
            "id",
            "pass_id",
            "guest_name",
            "guest_id_doc",
            "serial_number",
            "id_photo",
            "id_photo_url",
            "guard",
            "guard_username",
            "guard_name",
            "status",
            "flagged_as_stolen",
            "checked_in_at",
            "checked_out_at",
            "checkout_notes",
        ]
        read_only_fields = fields

    def get_guard_name(self, obj):
        if obj.guard:
            return obj.guard.get_full_name() or obj.guard.username
        return None

    def get_id_photo_url(self, obj):
        request = self.context.get("request")
        return serialize_image_value(obj.id_photo, request=request)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        ret["id_photo"] = serialize_image_value(instance.id_photo, request=request)
        ret["id_photo_url"] = ret["id_photo"]
        return ret


class GuestPassCheckOutSerializer(serializers.Serializer):
    """Guard submits decision after comparing the returned ID picture + serial with physical items."""
    pass_id = serializers.CharField(max_length=12)
    decision = serializers.ChoiceField(
        choices=["APPROVED", "DENIED", "STOLEN_FLAG", "STOLEN"],
        default="APPROVED",
        help_text="'APPROVED' to pass, 'STOLEN_FLAG' to decline and report as stolen, 'DENIED' to decline.",
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate_pass_id(self, value):
        return value.strip().upper()
