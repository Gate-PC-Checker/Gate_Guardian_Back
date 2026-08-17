import uuid
import secrets
from django.utils import timezone
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

    # Password setup / forced-change flow
    must_change_password = models.BooleanField(
        default=False,
        help_text="Forces user to set a new password before accessing the system"
    )
    password_setup_token = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    password_setup_token_created = models.DateTimeField(null=True, blank=True)

    def generate_password_setup_token(self):
        """Create a secure one-time token for password setup via email link."""
        token = secrets.token_urlsafe(32)
        self.password_setup_token = token
        self.password_setup_token_created = timezone.now()
        self.must_change_password = True
        return token

    def is_setup_token_valid(self, token: str, expiry_hours: int = 72) -> bool:
        if not self.password_setup_token or not self.password_setup_token_created:
            return False
        if self.password_setup_token != token:
            return False
        elapsed = timezone.now() - self.password_setup_token_created
        return elapsed.total_seconds() < expiry_hours * 3600

    def clear_password_setup_token(self):
        self.password_setup_token = None
        self.password_setup_token_created = None
        self.must_change_password = False

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
