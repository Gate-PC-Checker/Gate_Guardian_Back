from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsGuard, IsSuperAdminOrDPTAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import GuestPass
from .serializers import (
    GuestPassCreateSerializer,
    GuestPassSerializer,
    GuestPassCheckOutSerializer,
)


class GuestPassCheckInView(APIView):
    """
    Guard checks in a guest:
    POST /api/guests/check-in/
    Body (multipart or json): { id_photo?, serial_number, guest_name?, guest_id_doc? }
    Returns: { pass_id, id_photo_url, serial_number, checked_in_at, message }
    """
    permission_classes = [IsGuard]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = GuestPassCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        guest_pass = serializer.save(guard=request.user)
        pass_data = GuestPassSerializer(guest_pass).data
        return Response(
            {
                "pass_id": guest_pass.pass_id,
                "guest_name": guest_pass.guest_name,
                "guest_id_doc": guest_pass.guest_id_doc,
                "serial_number": guest_pass.serial_number,
                "id_photo_url": pass_data.get("id_photo_url") or (guest_pass.id_photo.url if guest_pass.id_photo else None),
                "checked_in_at": guest_pass.checked_in_at,
                "message": (
                    f"Guest registered. Unique Pass ID is '{guest_pass.pass_id}'."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class GuestPassLookupView(APIView):
    """
    Guard looks up a guest by Pass ID when they arrive to check out:
    GET /api/guests/lookup/<pass_id>/
    Returns: The stored ID picture, serial number, guest name, check-in time, and status.
    """
    permission_classes = [IsGuard]

    def get(self, request, pass_id, *args, **kwargs):
        clean_pass_id = pass_id.strip().upper()
        guest_pass = GuestPass.objects.filter(pass_id__iexact=clean_pass_id).first()
        if not guest_pass:
            return Response(
                {"detail": f"No guest pass found with ID '{pass_id}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = GuestPassSerializer(guest_pass).data
        return Response(data, status=status.HTTP_200_OK)


class GuestPassCheckOutView(APIView):
    """
    Guard submits verification decision after comparing the returned ID picture + serial:
    POST /api/guests/check-out/
    Body: { pass_id, decision: 'APPROVED' | 'STOLEN_FLAG' | 'DENIED', notes? }
    """
    permission_classes = [IsGuard]

    def post(self, request, *args, **kwargs):
        serializer = GuestPassCheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        pass_id = data["pass_id"]
        decision = data.get("decision", "APPROVED").upper()
        notes = data.get("notes", "")

        guest_pass = GuestPass.objects.filter(pass_id__iexact=pass_id).first()
        if not guest_pass:
            return Response(
                {"detail": f"No guest pass found with ID '{pass_id}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if guest_pass.status == GuestPass.Status.CHECKED_OUT:
            return Response(
                {
                    "detail": f"Guest pass '{pass_id}' has already been checked out.",
                    "checked_out_at": guest_pass.checked_out_at,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply guard decision
        guest_pass.submit_decision(decision, notes)

        is_stolen = guest_pass.flagged_as_stolen
        is_approved = guest_pass.status == GuestPass.Status.CHECKED_OUT

        msg = (
            "✅ Check-Out APPROVED: Device & Guest identity verified."
            if is_approved
            else (
                "🚨 STOLEN REPORT SUBMITTED: Security & Department have been alerted."
                if is_stolen
                else "⛔ Check-Out DENIED."
            )
        )

        return Response(
            {
                "pass_id": guest_pass.pass_id,
                "decision": guest_pass.status,
                "flagged_as_stolen": is_stolen,
                "checked_out_at": guest_pass.checked_out_at,
                "message": msg,
                "details": GuestPassSerializer(guest_pass).data,
            },
            status=status.HTTP_200_OK,
        )


class GuestPassListView(generics.ListAPIView):
    """
    GET /api/guests/
    Guard sees their own passes; DPT Admin / Super Admin sees department passes.
    """
    serializer_class = GuestPassSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = GuestPass.objects.select_related("guard").all()
        if user.is_guard:
            return qs.filter(guard=user)
        if user.is_dpt_admin:
            return qs.filter(guard__dpt=user.dpt)
        return qs
