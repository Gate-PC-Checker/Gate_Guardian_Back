from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


def serialize_image_value(image_field, request=None):
    if not image_field:
        return None

    if isinstance(image_field, str):
        url = image_field.strip()
    else:
        try:
            url = image_field.url
        except Exception:
            return None

    if not url:
        return None

    # Data URLs or blob URLs
    if url.startswith("data:") or url.startswith("blob:"):
        return url

    # Cloudinary URLs
    if "cloudinary.com" in url or "res.cloudinary.com" in url:
        return url

    # Extract relative /media/ path
    media_idx = url.find("/media/")
    if media_idx != -1:
        rel_path = url[media_idx:]
    elif url.startswith("http://") or url.startswith("https://"):
        return url
    else:
        rel_path = f"/media/{url.lstrip('/')}"

    if request is not None:
        try:
            return request.build_absolute_uri(rel_path)
        except Exception:
            pass

    if getattr(settings, "PUBLIC_URL", ""):
        return f"{settings.PUBLIC_URL.rstrip('/')}{rel_path}"

    return rel_path


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
        request = self.context.get("request")
        ret["profile_image"] = serialize_image_value(instance.profile_image, request=request)
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
        request = self.context.get("request")
        ret["profile_image"] = serialize_image_value(instance.profile_image, request=request)
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
        request = self.context.get("request")
        ret["profile_image"] = serialize_image_value(instance.profile_image, request=request)
        return ret


from django.db import models


class GateGuardTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role + user info into the JWT response payload with flexible case-insensitive matching."""

    def validate(self, attrs):
        identifier = attrs.get(self.username_field, "").strip()
        password = attrs.get("password", "")
        if identifier and password:
            # Find matching candidate users by username, email, or department code
            candidates = User.objects.filter(
                models.Q(username__iexact=identifier) |
                models.Q(email__iexact=identifier) |
                models.Q(dpt__code__iexact=identifier, role=User.Role.DPT_ADMIN)
            )
            for candidate in candidates:
                if candidate.check_password(password):
                    attrs[self.username_field] = candidate.username
                    break

        data = super().validate(attrs)
        data["role"] = self.user.role
        data["user_id"] = str(self.user.id)
        data["username"] = self.user.username
        data["first_name"] = self.user.first_name
        data["last_name"] = self.user.last_name
        data["email"] = self.user.email
        data["profile_image"] = serialize_image_value(self.user.profile_image)
        data["dpt_id"] = str(self.user.dpt_id) if self.user.dpt_id else None
        data["dpt_name"] = self.user.dpt.name if self.user.dpt else None
        data["dpt_code"] = self.user.dpt.code if self.user.dpt else None
        data["must_change_password"] = self.user.must_change_password
        return data
