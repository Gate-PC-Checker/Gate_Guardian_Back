from rest_framework import serializers
from .models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "code", "status", "profile_image", "created_at", "member_count", "device_count"]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_device_count(self, obj):
        return obj.devices.count()
