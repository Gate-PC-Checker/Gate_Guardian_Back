from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import IsSuperAdmin
from .models import Department
from .serializers import DepartmentRegisterSerializer, DepartmentSerializer


class DepartmentRegisterView(generics.CreateAPIView):
    serializer_class = DepartmentRegisterSerializer
    permission_classes = [IsSuperAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        department = result["department"]
        return Response(
            DepartmentSerializer(department).data,
            status=status.HTTP_201_CREATED,
        )


class DepartmentViewSet(viewsets.ModelViewSet):
    """Full CRUD, Super Admin only."""
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsSuperAdmin]

    @action(detail=True, methods=["patch"], url_path="profile-image")
    def profile_image(self, request, pk=None):
        department = self.get_object()

        allowed_fields = {"profile_image"}
        sent_fields = set(request.data.keys()).union(set(request.FILES.keys()))
        if sent_fields and not sent_fields.issubset(allowed_fields):
            return Response(
                {"detail": "Only profile_image can be updated from this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_data = request.FILES.get("profile_image") if "profile_image" in request.FILES else request.data.get("profile_image")
        serializer = self.get_serializer(
            department,
            data={"profile_image": image_data},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
