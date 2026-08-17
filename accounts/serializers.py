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
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone", "role", "dpt", "profile_image"]
        read_only_fields = ["id", "role"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["profile_image"] = serialize_image_value(instance.profile_image)
        return ret


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone", "role", "dpt", "password", "profile_image"]

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
            "profile_image",
        ]
        read_only_fields = ["id", "username", "first_name", "last_name", "email", "phone", "role", "dpt"]

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
        return data
