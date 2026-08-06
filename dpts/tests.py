from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from .models import Department


class DepartmentRegisterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_superadmin_can_create_department(self):
        superadmin = User.objects.create_user(
            username="superadmin",
            password="StrongPass123!",
            role=User.Role.SUPER_ADMIN,
            email="superadmin@example.com",
        )
        self.client.force_authenticate(superadmin)

        payload = {
            "name": "Computer Science",
            "code": "CSE",
            "head_name": "Alice Bekele",
            "email": "admin@cse.edu",
            "phone": "+251911000000",
            "password": "StrongPass123!",
        }

        response = self.client.post(reverse("department-register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["code"], "CSE")

        department = Department.objects.get(code="CSE")
        self.assertEqual(department.name, "Computer Science")

        user = User.objects.get(username="cse")
        self.assertEqual(user.role, User.Role.DPT_ADMIN)
        self.assertEqual(user.dpt, department)
        self.assertTrue(user.check_password("StrongPass123!"))
