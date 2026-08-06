from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsSuperAdminOrDPTAdmin, IsEmployee, IsGuard
from .models import PC
from .serializers import PCSerializer, PCLookupSerializer


class PCViewSet(viewsets.ModelViewSet):
    """
    Super Admin: sees/manages all PCs.
    DPT Admin: sees/manages PCs within their own DPT only.
    """
    serializer_class = PCSerializer
    permission_classes = [IsSuperAdminOrDPTAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = PC.objects.select_related("owner", "dpt").order_by("-created_at")
        if user.is_super_admin:
            return qs
        return qs.filter(dpt=user.dpt)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_dpt_admin:
            serializer.save(dpt=user.dpt)
        else:
            serializer.save()


class MyDevicesView(generics.ListAPIView):
    """Employee: view PCs assigned to them."""
    serializer_class = PCSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        return PC.objects.filter(owner=self.request.user).order_by("-created_at")


class PCLookupByTokenView(generics.RetrieveAPIView):
    """Guard scans a QR -> looks up device + owner before approve/deny decision."""
    serializer_class = PCLookupSerializer
    permission_classes = [IsGuard]
    lookup_field = "qr_token"
    lookup_url_kwarg = "qr_token"
    queryset = PC.objects.select_related("owner", "dpt").all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_serializer(instance).data
        data["stolen_alert"] = instance.status == PC.Status.STOLEN
        return Response(data, status=status.HTTP_200_OK)


class ReportLostDeviceView(generics.UpdateAPIView):
    """Employee reports their own device as lost/stolen."""
    serializer_class = PCSerializer
    permission_classes = [IsAuthenticated, IsEmployee]
    queryset = PC.objects.select_related("owner", "dpt").all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.owner_id != request.user.id:
            raise PermissionDenied("You can only report your own device.")

        instance.status = PC.Status.STOLEN
        instance.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)
