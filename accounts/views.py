import logging
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


def send_password_setup_email(user: User):
    """
    Send a welcome email with a one-time password setup link.
    Falls back to printing to console if email is not configured.
    """
    try:
        token = user.generate_password_setup_token()
        user.save(update_fields=["password_setup_token", "password_setup_token_created", "must_change_password"])

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8080").rstrip("/")
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
            "year": datetime.now().year,
        }

        html_body = render_to_string("accounts/password_setup_email.html", context)

        if not settings.EMAIL_HOST_USER:
            # No email credentials configured → log to console for dev
            logger.info(
                "\n========== [GateGuard] New Account Password Setup ===========\n"
                f"  User    : {user.username}\n"
                f"  Name    : {context['name']}\n"
                f"  Role    : {context['role_label']}\n"
                f"  Email   : {user.email or '(no email set)'}\n"
                f"  Link    : {setup_url}\n"
                "==============================================================\n"
            )
            print(
                f"\n[GateGuard] Password setup link for {user.username}: {setup_url}\n"
            )
            return

        if not user.email:
            logger.warning(f"User {user.username} has no email — skipping password setup email.")
            return

        email = EmailMessage(
            subject="[GateGuard] Set Up Your Account Password",
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        logger.info(f"Password setup email sent to {user.email} for user {user.username}.")

    except Exception as exc:
        logger.error(f"Failed to send password setup email for {user.username}: {exc}")


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

        # Send password setup email to the newly created user
        send_password_setup_email(user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["message"] = (
            "Account created. A password setup email has been sent to the user."
            if request.data.get("email")
            else "Account created. No email on file — share the setup link manually."
        )
        return response


class GuardCreateView(UserCreateView):
    """Department Admin creates guard accounts with a fixed GUARD role."""

    def perform_create(self, serializer):
        requester = self.request.user
        if not requester.is_dpt_admin:
            raise ValidationError({"detail": "Only department admins can create guards."})

        user = serializer.save(role=User.Role.GUARD, dpt=requester.dpt, must_change_password=True)
        send_password_setup_email(user)


class UserListView(generics.ListAPIView):
    serializer_class = CreateUserSerializer
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def get_queryset(self):
        requester = self.request.user
        if requester.is_super_admin:
            return User.objects.all().order_by("-date_joined")
        return User.objects.filter(dpt=requester.dpt).order_by("-date_joined")


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
        user = request.user
        current_password = request.data.get("current_password", "").strip()
        new_password = request.data.get("new_password", "").strip()

        if not new_password or len(new_password) < 6:
            return Response(
                {"detail": "New password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        if not new_password or len(new_password) < 6:
            return Response(
                {"detail": "Password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
    """
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "").strip()
        if not username:
            return Response({"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(username__iexact=username).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_super_admin:
            return Response({"detail": "Cannot resend setup email for super admin."}, status=status.HTTP_403_FORBIDDEN)

        send_password_setup_email(user)
        return Response({"detail": f"Password setup email resent for {user.username}."})


class ForgotPasswordResetView(generics.GenericAPIView):
    """Unauthenticated: reset password by username/email (no token required — for cases where user already logged in before)."""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("identifier", "").strip()
        email = request.data.get("email", "").strip()
        new_password = request.data.get("new_password", "").strip()

        if not identifier or not new_password:
            return Response(
                {"detail": "Please provide your username/ID and a new password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 6:
            return Response(
                {"detail": "Password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(username__iexact=identifier).first()
        if not user and email:
            user = User.objects.filter(email__iexact=email).first()

        if not user:
            return Response(
                {"detail": "No account found matching the provided details."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_super_admin:
            return Response(
                {"detail": "Super Admin password cannot be reset via this portal."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if email and user.email and user.email.lower() != email.lower():
            return Response(
                {"detail": "The provided email does not match our records for this ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.clear_password_setup_token()
        user.save()
        return Response({"detail": "Password reset successfully. You can now log in with your new password."})
