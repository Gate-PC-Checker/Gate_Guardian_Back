from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import IsSuperAdmin
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """Full CRUD, Super Admin only."""
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsSuperAdmin]

    @action(detail=True, methods=["patch"], url_path="profile-image")
    def profile_image(self, request, pk=None):
        department = self.get_object()

        allowed_fields = {"profile_image"}
        sent_fields = set(request.data.keys())
        if sent_fields and not sent_fields.issubset(allowed_fields):
            return Response(
                {"detail": "Only profile_image can be updated from this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            department,
            data={"profile_image": request.data.get("profile_image")},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
