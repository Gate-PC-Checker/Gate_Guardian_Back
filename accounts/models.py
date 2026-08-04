import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        DPT_ADMIN = "DPT_ADMIN", "DPT Admin"
        EMPLOYEE = "EMPLOYEE", "Employee"
        GUARD = "GUARD", "Guard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices)
    dpt = models.ForeignKey(
        "dpts.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
        help_text="Required for DPT_ADMIN and EMPLOYEE roles",
    )
    phone = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to="users/profile_images/", blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_dpt_admin(self):
        return self.role == self.Role.DPT_ADMIN

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_guard(self):
        return self.role == self.Role.GUARD
