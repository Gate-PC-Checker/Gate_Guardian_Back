from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


def serialize_image_value(image_field):
    if not image_field:
        return None

    if isinstance(image_field, str):
        return image_field

    try:
        url = image_field.url
        if url.startswith("/") and settings.PUBLIC_URL:
            return f"{settings.PUBLIC_URL}{url}"
        return url
    except Exception:
        return None


class UserSerializer(serializers.ModelSerializer):
    dpt_name = serializers.CharField(source="dpt.name", read_only=True)
    dpt_code = serializers.CharField(source="dpt.code", read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email", "phone",
            "role", "dpt", "dpt_name", "dpt_code", "profile_image"
        ]
        read_only_fields = ["id", "role"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["profile_image"] = serialize_image_value(instance.profile_image)
        return ret


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    dpt_name = serializers.CharField(source="dpt.name", read_only=True)
    dpt_code = serializers.CharField(source="dpt.code", read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email", "phone",
            "role", "dpt", "dpt_name", "dpt_code", "password", "profile_image"
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["profile_image"] = serialize_image_value(instance.profile_image)
        return ret


class MeProfileSerializer(serializers.ModelSerializer):
    dpt_name = serializers.CharField(source="dpt.name", read_only=True)
    dpt_code = serializers.CharField(source="dpt.code", read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "dpt",
            "dpt_name",
            "dpt_code",
            "profile_image",
            "must_change_password",
        ]
        read_only_fields = ["id", "username", "first_name", "last_name", "email", "phone", "role", "dpt", "must_change_password"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["profile_image"] = serialize_image_value(instance.profile_image)
        return ret


class GateGuardTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role + user info into the JWT response payload."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["user_id"] = str(self.user.id)
        data["username"] = self.user.username
        data["dpt_id"] = str(self.user.dpt_id) if self.user.dpt_id else None
        data["dpt_name"] = self.user.dpt.name if self.user.dpt else None
        data["dpt_code"] = self.user.dpt.code if self.user.dpt else None
        data["must_change_password"] = self.user.must_change_password
        return data
