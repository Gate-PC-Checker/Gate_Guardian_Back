from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
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
            serializer.save(role=User.Role.EMPLOYEE, dpt=requester.dpt)
        else:
            serializer.save()


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
        sent_fields = set(request.data.keys())
        if sent_fields and not sent_fields.issubset(allowed_fields):
            return Response(
                {"detail": "Only profile_image can be updated from this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)
