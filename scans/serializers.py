from rest_framework import serializers
from devices.models import PC
from .models import ScanLog


class ScanLogCreateSerializer(serializers.ModelSerializer):
    qr_token = serializers.UUIDField(write_only=True)

    class Meta:
        model = ScanLog
        fields = ["id", "qr_token", "scan_type", "result", "photo_evidence", "notes", "scanned_at"]
        read_only_fields = ["id", "scanned_at"]

    def validate(self, attrs):
        # Resolve the device from the QR token
        try:
            attrs["pc"] = PC.objects.get(qr_token=attrs.pop("qr_token"))
        except PC.DoesNotExist:
            raise serializers.ValidationError({"qr_token": "No device found for this QR code."})

        # For CHECK_OUT: verify that the device has a prior approved CHECK_IN
        if attrs.get("scan_type") == ScanLog.ScanType.CHECK_OUT:
            has_approved_checkin = ScanLog.objects.filter(
                pc=attrs["pc"],
                scan_type=ScanLog.ScanType.CHECK_IN,
                result=ScanLog.Result.APPROVED,
            ).exists()
            if not has_approved_checkin:
                raise serializers.ValidationError(
                    {
                        "scan_type": (
                            "Cannot check out: this device has no approved check-in on record. "
                            "The device must be checked in before it can be checked out."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        pc = validated_data["pc"]
        # Stolen devices always get flagged regardless of what the guard submits
        if pc.status == PC.Status.STOLEN:
            validated_data["result"] = ScanLog.Result.STOLEN_FLAG
        validated_data["guard"] = self.context["request"].user
        return super().create(validated_data)


class ScanLogSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="pc.asset_tag", read_only=True)
    guard_username = serializers.CharField(source="guard.username", read_only=True)

    class Meta:
        model = ScanLog
        fields = [
            "id", "pc", "asset_tag", "guard", "guard_username",
            "scan_type", "result", "photo_evidence", "notes", "scanned_at",
        ]
