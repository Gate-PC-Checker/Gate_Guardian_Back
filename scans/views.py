from rest_framework import generics, status
from rest_framework.response import Response
from accounts.permissions import IsGuard, IsSuperAdminOrDPTAdmin
from devices.models import PC
from .models import ScanLog
from .serializers import ScanLogCreateSerializer, ScanLogSerializer


class ScanCreateView(generics.CreateAPIView):
    """Guard submits an approve/deny decision after scanning a QR, with a check-in or check-out type."""
    serializer_class = ScanLogCreateSerializer
    permission_classes = [IsGuard]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan = serializer.save()
        response_data = ScanLogSerializer(scan).data
        response_data["stolen_alert"] = scan.result == ScanLog.Result.STOLEN_FLAG
        return Response(response_data, status=status.HTTP_201_CREATED)


class ScanLogListView(generics.ListAPIView):
    """Audit trail — Super Admin sees all, DPT Admin sees their department's scans."""
    serializer_class = ScanLogSerializer
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = ScanLog.objects.select_related("pc", "guard").all()
        if user.is_super_admin:
            return qs
        return qs.filter(pc__dpt=user.dpt)
