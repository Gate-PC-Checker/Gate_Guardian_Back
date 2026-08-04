from rest_framework import serializers
from .models import Department


def serialize_image_value(image_field):
    if not image_field:
        return None

    if isinstance(image_field, str):
        return image_field

    try:
        return image_field.url
    except Exception:
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "code", "status", "profile_image", "created_at", "member_count", "device_count"]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_device_count(self, obj):
        return obj.devices.count()

    def get_profile_image(self, obj):
        return serialize_image_value(obj.profile_image)
