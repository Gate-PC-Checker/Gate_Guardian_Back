from django.conf import settings
from rest_framework import serializers

from accounts.models import User
from accounts.views import send_password_setup_email
from accounts.serializers import serialize_image_value
from .models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "status", "profile_image", "created_at", "member_count", "device_count"]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_device_count(self, obj):
        return obj.devices.count()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        ret["profile_image"] = serialize_image_value(instance.profile_image, request=request)
        return ret


class DepartmentRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    code = serializers.CharField(max_length=20)
    head_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_code(self, value):
        value = value.strip().upper()
        if Department.objects.filter(code=value).exists():
            raise serializers.ValidationError("Department code already exists")
        return value

    def create(self, validated_data):
        department = Department.objects.create(
            name=validated_data["name"].strip(),
            code=validated_data["code"].strip().upper(),
        )

        username = validated_data["code"].strip().lower()
        user = User.objects.create_user(
            username=username,
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["head_name"].split()[0] if validated_data["head_name"] else "Head",
            last_name=" ".join(validated_data["head_name"].split()[1:]) if validated_data["head_name"] else "",
            phone=validated_data.get("phone", ""),
            role=User.Role.DPT_ADMIN,
            dpt=department,
            must_change_password=True,
        )
        user.save()
        send_password_setup_email(user)
        return {"department": department, "user": user}
