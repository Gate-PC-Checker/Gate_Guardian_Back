from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from .models import User
from .serializers import CreateUserSerializer, GateGuardTokenObtainPairSerializer, MeProfileSerializer
from .permissions import IsSuperAdmin, IsSuperAdminOrDPTAdmin


class LoginView(TokenObtainPairView):
    """POST username + password -> access, refresh, role, user_id, dpt_id."""
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
            serializer.save(role=role, dpt=requester.dpt)
        else:
            serializer.save()


class GuardCreateView(UserCreateView):
    """Department Admin creates guard accounts with a fixed GUARD role."""

    def perform_create(self, serializer):
        requester = self.request.user
        if not requester.is_dpt_admin:
            raise ValidationError({"detail": "Only department admins can create guards."})

        serializer.save(role=User.Role.GUARD, dpt=requester.dpt)


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
    """Allows an authenticated user (or first-time login) to change their password securely."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not new_password or len(new_password) < 6:
            return Response(
                {"detail": "New password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if current_password and not user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password updated successfully."})


class ForgotPasswordResetView(generics.GenericAPIView):
    """Allows employees/department admins to reset their password using their registered username/email and ID."""
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

        # Disallow superadmin reset from public endpoint for security
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
        user.save()
        return Response({"detail": "Password reset successfully. You can now log in with your new password."})
