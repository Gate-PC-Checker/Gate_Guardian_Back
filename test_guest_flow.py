import io
import os
import django
from PIL import Image

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gateguard.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from accounts.models import User
from dpts.models import Department
from guests.models import GuestPass


def create_sample_id_image():
    """Create a sample image simulating a guest ID / passport picture."""
    file = io.BytesIO()
    image = Image.new("RGB", (400, 250), color="#1A237E")
    image.save(file, "JPEG")
    file.seek(0)
    return SimpleUploadedFile("guest_national_id.jpg", file.read(), content_type="image/jpeg")


def main():
    print("=" * 60)
    print("🚀 GATEGUARD GUEST PASS BACKEND END-TO-END TEST")
    print("=" * 60)

    # 1. Setup guard & department
    dept, _ = Department.objects.get_or_create(code="SEC_GATE", defaults={"name": "Main Gate Security"})
    guard, created = User.objects.get_or_create(
        username="gate_officer_test",
        defaults={
            "first_name": "Officer",
            "last_name": "Kebede",
            "role": User.Role.GUARD,
            "dpt": dept,
        }
    )
    if created:
        guard.set_password("guard123")
        guard.save()

    client = APIClient()
    client.force_authenticate(user=guard)
    print(f"\n[1] Authenticated as Guard: {guard.username} ({dept.name})")

    # 2. Test Guest Check-In (Guard takes picture of ID + enters serial number)
    print("\n[2] Testing Guest Check-In with ID Photo and Device Serial Number...")
    sample_photo = create_sample_id_image()
    checkin_data = {
        "guest_name": "Dawit Haile",
        "serial_number": "SN-MACBOOK-PRO-9988",
        "id_photo": sample_photo,
    }

    checkin_resp = client.post("/api/guests/check-in/", checkin_data, format="multipart")
    print(f"    Status Code: {checkin_resp.status_code}")
    assert checkin_resp.status_code == 201, f"Expected 201, got {checkin_resp.status_code}"

    pass_id = checkin_resp.data["pass_id"]
    photo_url = checkin_resp.data.get("id_photo_url")
    print(f"    ✅ Check-In SUCCESS!")
    print(f"    🏷️  Auto-Generated Unique Pass ID: {pass_id}")
    print(f"    💻 Recorded Serial Number: {checkin_resp.data['serial_number']}")
    print(f"    📷 ID Photo URL: {photo_url}")
    print(f"    ⏰ Checked in at: {checkin_resp.data['checked_in_at']}")

    # 3. Test Guest Check-Out Lookup (Guest mentions Pass ID to guard at departure)
    print(f"\n[3] Testing Check-Out Lookup by Pass ID '{pass_id}'...")
    lookup_resp = client.get(f"/api/guests/lookup/{pass_id}/")
    print(f"    Status Code: {lookup_resp.status_code}")
    assert lookup_resp.status_code == 200, f"Expected 200, got {lookup_resp.status_code}"

    lookup_data = lookup_resp.data
    print(f"    ✅ Lookup SUCCESS!")
    print(f"    👤 Guest Name: {lookup_data['guest_name']}")
    print(f"    💻 Stored Serial Number: {lookup_data['serial_number']}")
    print(f"    📷 Stored ID Photo: {lookup_data['id_photo_url']}")
    print(f"    🟢 Current Status: {lookup_data['status']}")

    # 4. Test Check-Out Decision: APPROVE / PASS
    print(f"\n[4] Testing Check-Out Decision -> 'APPROVED' (Identity & device match)...")
    checkout_resp = client.post(
        "/api/guests/check-out/",
        {
            "pass_id": pass_id,
            "decision": "APPROVED",
            "notes": "Physical ID and laptop serial matched correctly.",
        },
        format="json",
    )
    print(f"    Status Code: {checkout_resp.status_code}")
    assert checkout_resp.status_code == 200, f"Expected 200, got {checkout_resp.status_code}"
    print(f"    ✅ Decision Response: {checkout_resp.data['message']}")
    print(f"    🏷️  Final Status: {checkout_resp.data['decision']}")
    print(f"    🛡️  Flagged as Stolen: {checkout_resp.data['flagged_as_stolen']}")

    # 5. Test Stolen Flagging Flow with another guest
    print("\n[5] Testing Check-Out Decision -> 'STOLEN_FLAG' (Device mismatch / stolen)...")
    stolen_photo = create_sample_id_image()
    checkin_stolen = client.post(
        "/api/guests/check-in/",
        {
            "guest_name": "Suspicious Visitor",
            "serial_number": "SN-HP-ENVY-1122",
            "id_photo": stolen_photo,
        },
        format="multipart",
    )
    stolen_pass_id = checkin_stolen.data["pass_id"]
    print(f"    Created new pass for test: {stolen_pass_id}")

    flag_resp = client.post(
        "/api/guests/check-out/",
        {
            "pass_id": stolen_pass_id,
            "decision": "STOLEN_FLAG",
            "notes": "Serial number on physical laptop differs from check-in record.",
        },
        format="json",
    )
    print(f"    Status Code: {flag_resp.status_code}")
    assert flag_resp.status_code == 200, f"Expected 200, got {flag_resp.status_code}"
    print(f"    🚨 Stolen Flag Response: {flag_resp.data['message']}")
    print(f"    🛡️  Flagged as Stolen: {flag_resp.data['flagged_as_stolen']}")

    print("\n" + "=" * 60)
    print("🎉 ALL BACKEND API FLOWS TESTED & VERIFIED 100% WORKING!")
    print("=" * 60)


if __name__ == "__main__":
    main()
