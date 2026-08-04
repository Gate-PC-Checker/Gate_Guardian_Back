from rest_framework import viewsets
from accounts.permissions import IsSuperAdmin
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """Full CRUD, Super Admin only."""
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsSuperAdmin]
