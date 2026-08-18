import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from dpts.models import Department
from guests.models import GuestPass


def create_dummy_image():
    file = io.BytesIO()
    image = Image.new("RGB", (100, 100), color="blue")
    image.save(file, "JPEG")
    file.seek(0)
    return SimpleUploadedFile("test_id.jpg", file.read(), content_type="image/jpeg")


class GuestPassAPITests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Security Dpt", code="SEC")

        self.guard = User.objects.create_user(
            username="guard_john",
            password="password123",
            role=User.Role.GUARD,
            dpt=self.department,
        )

        self.dept2 = Department.objects.create(name="Main Campus", code="MAIN")
        self.guard2 = User.objects.create_user(
            username="guard_bob",
            password="password123",
            role=User.Role.GUARD,
            dpt=self.dept2,
        )

        self.dept_admin = User.objects.create_user(
            username="admin_sec",
            password="password123",
            role=User.Role.DPT_ADMIN,
            dpt=self.department,
        )

        self.employee = User.objects.create_user(
            username="emp_alice",
            password="password123",
            role=User.Role.EMPLOYEE,
            dpt=self.department,
        )

        self.client = APIClient()

    def test_guard_check_in_with_photo_and_serial(self):
        self.client.force_authenticate(user=self.guard)
        photo = create_dummy_image()
        response = self.client.post(
            "/api/guests/check-in/",
            {
                "guest_name": "Abebe Bikila",
                "serial_number": "SN-DELL-5520",
                "id_photo": photo,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("pass_id", response.data)
        pass_id = response.data["pass_id"]
        self.assertTrue(pass_id.startswith("GST-"))
        self.assertEqual(response.data["serial_number"], "SN-DELL-5520")

        # Verify DB
        guest_pass = GuestPass.objects.get(pass_id=pass_id)
        self.assertEqual(guest_pass.guest_name, "Abebe Bikila")
        self.assertEqual(guest_pass.serial_number, "SN-DELL-5520")
        self.assertTrue(bool(guest_pass.id_photo))
        self.assertEqual(guest_pass.status, GuestPass.Status.ACTIVE)

    def test_guard_lookup_pass_for_checkout(self):
        guest_pass = GuestPass.objects.create(
            guest_name="Chala Tufa",
            serial_number="MACBOOK-M2-8877",
            guard=self.guard,
            status=GuestPass.Status.ACTIVE,
        )

        self.client.force_authenticate(user=self.guard)
        response = self.client.get(f"/api/guests/lookup/{guest_pass.pass_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pass_id"], guest_pass.pass_id)
        self.assertEqual(response.data["serial_number"], "MACBOOK-M2-8877")
        self.assertEqual(response.data["guest_name"], "Chala Tufa")

    def test_guard_checkout_approve(self):
        guest_pass = GuestPass.objects.create(
            guest_name="Chala Tufa",
            serial_number="MACBOOK-M2-8877",
            guard=self.guard,
            status=GuestPass.Status.ACTIVE,
        )

        self.client.force_authenticate(user=self.guard)
        response = self.client.post(
            "/api/guests/check-out/",
            {
                "pass_id": guest_pass.pass_id,
                "decision": "APPROVED",
                "notes": "Verified ID and device",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["flagged_as_stolen"])
        guest_pass.refresh_from_db()
        self.assertEqual(guest_pass.status, GuestPass.Status.CHECKED_OUT)
        self.assertFalse(guest_pass.flagged_as_stolen)

    def test_guard_checkout_report_stolen(self):
        guest_pass = GuestPass.objects.create(
            guest_name="Sara Connor",
            serial_number="LENOVO-T14-ORIGINAL",
            guard=self.guard,
            status=GuestPass.Status.ACTIVE,
        )

        self.client.force_authenticate(user=self.guard)
        response = self.client.post(
            "/api/guests/check-out/",
            {
                "pass_id": guest_pass.pass_id,
                "decision": "STOLEN_FLAG",
                "notes": "Serial number does not match device carrying",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["flagged_as_stolen"])
        guest_pass.refresh_from_db()
        self.assertEqual(guest_pass.status, GuestPass.Status.STOLEN_FLAG)
        self.assertTrue(guest_pass.flagged_as_stolen)
