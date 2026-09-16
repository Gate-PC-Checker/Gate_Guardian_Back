import logging
import re
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import CreateUserSerializer, GateGuardTokenObtainPairSerializer, MeProfileSerializer
from .permissions import IsSuperAdmin, IsSuperAdminOrDPTAdmin

logger = logging.getLogger(__name__)


def validate_strong_password(password: str) -> None:
    """
    Enforces a strong password policy:
    - At least 8 characters
    - Must contain at least one letter (a-z or A-Z)
    - Must contain at least one number or special character
    - Disallow trivial common passwords
    """
    if not password or len(password) < 8:
        raise ValidationError({"detail": "Password must be at least 8 characters long."})
    if not re.search(r"[A-Za-z]", password):
        raise ValidationError({"detail": "Password must contain at least one letter."})
    if not re.search(r"[0-9!@#$%^&*(),.?\":{}|<>\-_]", password):
        raise ValidationError({"detail": "Password must contain at least one number or symbol."})
    if password.lower() in {"password", "12345678", "password123", "gateguard", "admin123"}:
        raise ValidationError({"detail": "This password is too common. Please choose a more secure password."})



def send_password_setup_email(user: User, is_reset: bool = False):
    """
    Send a welcome or password reset email with a one-time password setup/reset link.
    Supports HTTP-based APIs (Brevo, Resend) to bypass SMTP port blocking on hosts like Render.
    Always generates and saves the setup token, and returns (email_sent: bool, setup_url: str, error: str | None).
    """
    token = user.generate_password_setup_token()
    user.save(update_fields=["password_setup_token", "password_setup_token_created", "must_change_password"])

    frontend_url = getattr(settings, "FRONTEND_URL", "https://front-end-chi-gold.vercel.app").rstrip("/")
    setup_url = f"{frontend_url}/setup-password?token={token}"

    role_labels = {
        User.Role.EMPLOYEE: "Employee",
        User.Role.DPT_ADMIN: "Department Admin",
        User.Role.GUARD: "Security Guard",
    }

    context = {
        "name": user.get_full_name() or user.username,
        "username": user.username,
        "role_label": role_labels.get(user.role, user.role),
        "department": user.dpt.name if user.dpt else None,
        "setup_url": setup_url,
        "is_reset": is_reset,
        "year": datetime.now().year,
    }

    html_body = render_to_string("accounts/password_setup_email.html", context)
    subject = "[GateGuard] Reset Your Account Password" if is_reset else "[GateGuard] Set Up Your Account Password"

    if not user.email:
        logger.warning(f"User {user.username} has no email — skipping email delivery.")
        return False, setup_url, "User has no email"

    # 1. Try Brevo HTTPS API if key configured
    brevo_key = getattr(settings, "BREVO_API_KEY", "")
    if brevo_key:
        try:
            import json, urllib.request
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=json.dumps({
                    "sender": {"name": "GateGuard", "email": getattr(settings, "EMAIL_HOST_USER", "mekdelawitkassa6@gmail.com")},
                    "to": [{"email": user.email, "name": context["name"]}],
                    "subject": subject,
                    "htmlContent": html_body,
                }).encode("utf-8"),
                headers={
                    "api-key": brevo_key,
                    "Content-Type": "application/json",
                    "User-Agent": "GateGuard/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Password reset/setup email sent via Brevo to {user.email}.")
                    return True, setup_url, None
        except Exception as exc:
            logger.error(f"Brevo email failed: {exc}")

    # 2. Try Resend HTTPS API if key configured
    resend_key = getattr(settings, "RESEND_API_KEY", "")
    if resend_key:
        try:
            import json, urllib.request
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": getattr(settings, "DEFAULT_FROM_EMAIL", "GateGuard <onboarding@resend.dev>"),
                    "to": [user.email],
                    "subject": subject,
                    "html": html_body,
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "GateGuard/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Password reset/setup email sent via Resend to {user.email}.")
                    return True, setup_url, None
        except Exception as exc:
            logger.error(f"Resend email failed: {exc}")

    # 3. Try standard Django SMTP (with timeout handling)
    if getattr(settings, "EMAIL_HOST_USER", None):
        try:
            email = EmailMessage(
                subject=subject,
                body=html_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.content_subtype = "html"
            email.send(fail_silently=False)
            logger.info(f"Password reset/setup email sent via SMTP to {user.email}.")
            return True, setup_url, None
        except Exception as exc:
            logger.warning(f"SMTP send failed (often blocked by host firewall on ports 25/465/587): {exc}")
            return False, setup_url, str(exc)

    return False, setup_url, "No email provider configured"


class LoginView(TokenObtainPairView):
    """POST username + password → access, refresh, role, user_id, dpt_id, must_change_password."""
    serializer_class = GateGuardTokenObtainPairSerializer


class UserCreateView(generics.CreateAPIView):
    """Super Admin creates DPT Admins / Guards. DPT Admin creates Employees in their own DPT."""
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def perform_create(self, serializer):
        requester = self.request.user
        if requester.is_dpt_admin:
            requested_role = self.request.data.get("role", User.Role.EMPLOYEE)
            if requested_role not in {User.Role.EMPLOYEE, User.Role.GUARD}:
                raise ValidationError({"role": "Department admins can only create EMPLOYEE or GUARD users."})

            role = User.Role.GUARD if requested_role == User.Role.GUARD else User.Role.EMPLOYEE
            user = serializer.save(role=role, dpt=requester.dpt, must_change_password=True)
        else:
            user = serializer.save(must_change_password=True)

        sent, setup_url, error = send_password_setup_email(user)
        self._email_sent = sent
        self._setup_url = setup_url
        self._email_error = error

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        email_sent = getattr(self, "_email_sent", False)
        setup_url = getattr(self, "_setup_url", None)
        email_error = getattr(self, "_email_error", None)

        response.data["setup_url"] = setup_url
        response.data["email_sent"] = email_sent
        if email_sent:
            response.data["message"] = "Account created. A password setup email has been sent to the user."
        else:
            response.data["message"] = "Account created. Setup link generated — you can copy and share it directly."
            if email_error:
                response.data["email_error"] = email_error
        return response


class GuardCreateView(UserCreateView):
    """Department Admin creates guard accounts with a fixed GUARD role."""

    def perform_create(self, serializer):
        requester = self.request.user
        if not requester.is_dpt_admin:
            raise ValidationError({"detail": "Only department admins can create guards."})

        user = serializer.save(role=User.Role.GUARD, dpt=requester.dpt, must_change_password=True)
        sent, setup_url, error = send_password_setup_email(user)
        self._email_sent = sent
        self._setup_url = setup_url
        self._email_error = error



class UserListView(generics.ListAPIView):
    serializer_class = CreateUserSerializer
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def get_queryset(self):
        requester = self.request.user
        if requester.is_super_admin:
            return User.objects.all().order_by("-date_joined")
        return User.objects.filter(dpt=requester.dpt).order_by("-date_joined")


class UserDetailDestroyView(generics.RetrieveDestroyAPIView):
    """
    Super Admin can delete any user.
    Department Admin can delete Employee or Guard users in their department.
    """
    serializer_class = CreateUserSerializer
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def get_queryset(self):
        requester = self.request.user
        if requester.is_super_admin:
            return User.objects.all()
        return User.objects.filter(dpt=requester.dpt).exclude(role=User.Role.SUPER_ADMIN)

    def perform_destroy(self, instance):
        requester = self.request.user
        if instance.id == requester.id:
            raise ValidationError({"detail": "You cannot delete your own account."})
        if requester.is_dpt_admin and instance.role == User.Role.DPT_ADMIN and instance.id != requester.id:
            raise ValidationError({"detail": "Department admins cannot delete other department admins."})
        instance.delete()


class MeProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        allowed_fields = {"profile_image"}
        sent_fields = set(request.data.keys()).union(set(request.FILES.keys()))
        if sent_fields and not sent_fields.issubset(allowed_fields):
            return Response(
                {"detail": "Only profile_image can be updated from this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)


class ChangePasswordView(generics.GenericAPIView):
    """Authenticated user changes their own password (also clears must_change_password flag)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        current_password = request.data.get("current_password", "").strip()
        new_password = request.data.get("new_password", "").strip()

        if not new_password:
            return Response(
                {"detail": "New password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validate_strong_password(new_password)

        user = request.user

        # current_password check only needed if they already have a real password set
        if current_password and not user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.clear_password_setup_token()
        user.save()
        return Response({"detail": "Password updated successfully. You can now log in."})


class SetupPasswordView(generics.GenericAPIView):
    """
    Unauthenticated endpoint: accepts a one-time token (from email) and sets a new password.
    Used for first-time password setup by new employees and department admins.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get("token", "").strip()
        new_password = request.data.get("new_password", "").strip()

        if not token:
            return Response(
                {"detail": "Setup token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validate_strong_password(new_password)

        user = User.objects.filter(password_setup_token=token).first()
        if not user:
            return Response(
                {"detail": "Invalid or expired setup link. Please contact your administrator."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_setup_token_valid(token):
            return Response(
                {"detail": "This setup link has expired (72 hours). Please contact your administrator for a new link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.clear_password_setup_token()
        user.save()

        return Response({
            "detail": "Password set successfully. You can now log in.",
            "username": user.username,
            "role": user.role,
        })


class ResendSetupEmailView(generics.GenericAPIView):
    """
    Admin-only: resend the password setup email for a user who hasn't set up their account yet.
    Accepts either { "username": "..." } or { "user_id": "<uuid>" }.
    """
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "").strip()
        user_id = request.data.get("user_id", "").strip()

        if not username and not user_id:
            return Response({"detail": "Provide either 'username' or 'user_id'."}, status=status.HTTP_400_BAD_REQUEST)

        if user_id:
            user = User.objects.filter(id=user_id).first()
        else:
            user = User.objects.filter(username__iexact=username).first()

        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_super_admin:
            return Response({"detail": "Cannot resend setup email for super admin."}, status=status.HTTP_403_FORBIDDEN)

        # DPT admin can only resend for users in their own department
        if request.user.is_dpt_admin and user.dpt_id != request.user.dpt_id:
            return Response({"detail": "You can only resend emails for users in your department."}, status=status.HTTP_403_FORBIDDEN)

        if not user.email:
            return Response(
                {"detail": f"User {user.username} has no email address. Please update their profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sent, setup_url, error = send_password_setup_email(user, is_reset=user.must_change_password)
        if not sent:
            return Response({
                "detail": "Setup link generated. You can copy and share it directly with the user.",
                "setup_url": setup_url,
                "email_sent": False,
                "email_error": error,
            })

        return Response({
            "detail": f"Password setup email sent to {user.email} for {user.username}.",
            "setup_url": setup_url,
            "email_sent": True,
        })


class ForgotPasswordResetView(generics.GenericAPIView):
    """
    Unauthenticated endpoint: Sends a secure password reset email link.
    POST /api/auth/forgot-password/
    Body: { "identifier": "username_or_email" }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        identifier = (
            request.data.get("identifier")
            or request.data.get("email")
            or request.data.get("username")
            or ""
        ).strip()
        new_password = request.data.get("new_password", "").strip()
        token = request.data.get("token", "").strip()

        if not identifier and not token:
            return Response(
                {"detail": "Please provide your username or registered email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If token and new_password are provided directly (e.g. from reset link web form)
        if token and new_password:
            validate_strong_password(new_password)
            user = User.objects.filter(password_setup_token=token).first()
            if not user or not user.is_setup_token_valid(token):
                return Response(
                    {"detail": "Invalid or expired password reset link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_password(new_password)
            user.clear_password_setup_token()
            user.save()
            return Response({"detail": "Password reset successfully. You can now log in."})

        # Flexible account lookup by username, email, or department code
        user = (
            User.objects.filter(username__iexact=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(dpt__code__iexact=identifier, role=User.Role.DPT_ADMIN).first()
        )

        if not user:
            return Response(
                {"detail": f"No account found matching '{identifier}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_super_admin:
            return Response(
                {"detail": "Super Admin password cannot be reset via this portal."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.email:
            return Response(
                {"detail": "No email address is associated with this account. Please contact your department administrator to set your password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Send password reset email
        send_password_setup_email(user, is_reset=True)

        # Mask email for privacy (e.g. j***e@example.com)
        parts = user.email.split("@")
        if len(parts) == 2:
            uname, domain = parts
            masked_uname = uname[0] + "***" + (uname[-1] if len(uname) > 1 else "")
            masked_email = f"{masked_uname}@{domain}"
        else:
            masked_email = user.email

        return Response({
            "detail": f"A password reset link has been sent to your email ({masked_email}). Please open your email, reset your password, and then return to log in.",
            "email_sent": True,
            "username": user.username,
        })
