from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from dpts.models import Department


class DepartmentUserCreationTests(TestCase):
	def setUp(self):
		self.department = Department.objects.create(name="IT Center", code="ITC")
		self.department_admin = User.objects.create_user(
			username="it_admin",
			password="testpass123",
			role=User.Role.DPT_ADMIN,
			dpt=self.department,
		)
		self.client = APIClient()
		self.client.force_authenticate(user=self.department_admin)

	def test_department_admin_creates_guard_with_guard_role(self):
		response = self.client.post(
			"/api/auth/users/create/",
			{
				"username": "guard1",
				"first_name": "Guard",
				"last_name": "One",
				"email": "guard1@example.com",
				"phone": "+251911234567",
				"password": "testpass123",
				"role": "GUARD",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		created_user = User.objects.get(username="guard1")
		self.assertEqual(created_user.role, User.Role.GUARD)
		self.assertEqual(created_user.dpt, self.department)

	def test_department_admin_rejects_invalid_role(self):
		response = self.client.post(
			"/api/auth/users/create/",
			{
				"username": "invalid",
				"first_name": "Invalid",
				"last_name": "Role",
				"email": "invalid@example.com",
				"phone": "+251911234568",
				"password": "testpass123",
				"role": "SUPER_ADMIN",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("role", response.data)
