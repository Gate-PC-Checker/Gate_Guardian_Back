from rest_framework import serializers
from accounts.serializers import serialize_image_value
from .models import PC


class PCSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    dpt_name = serializers.CharField(source="dpt.name", read_only=True)
    qr_image = serializers.SerializerMethodField()

    class Meta:
        model = PC
        fields = [
            "id", "qr_token", "asset_tag", "brand", "model_name", "serial_number",
            "owner", "owner_name", "owner_username", "dpt", "dpt_name",
            "status", "qr_image", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "qr_token", "qr_image", "created_at", "updated_at"]

    def get_qr_image(self, obj):
        return serialize_image_value(obj.qr_image, request=self.context.get("request"))


class PCLookupSerializer(serializers.ModelSerializer):
    """What a Guard sees when they scan a QR — just enough to verify ownership."""
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    owner_photo = serializers.SerializerMethodField()
    dpt_name = serializers.CharField(source="dpt.name", read_only=True)

    class Meta:
        model = PC
        fields = [
            "id", "asset_tag", "brand", "model_name",
            "owner_name", "owner_username", "owner_photo",
            "dpt_name", "status",
        ]

    def get_owner_photo(self, obj):
        if obj.owner and getattr(obj.owner, "profile_image", None):
            return serialize_image_value(obj.owner.profile_image, request=self.context.get("request"))
        return None
