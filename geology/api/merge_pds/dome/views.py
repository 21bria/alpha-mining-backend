from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from master.api.base import MasterBaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
    user_allowed_iup_ids,
)

from geology.models import DomeMerge
from .serializers import DomeMergeSerializer
from geology.services.dome_merge import undo_dome_merge


class DomeMergeViewSet(MasterBaseViewSet):
    queryset = DomeMerge.objects.select_related(
        "iup",
        "original_dome",
        "dome_second",
        "user",
        "undone_by",
    ).all().order_by("-id")

    serializer_class = DomeMergeSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "ref_id",
        "status",
        "description",
        "original_dome__code",
        "original_dome__name",
        "dome_second__code",
        "dome_second__name",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
        "undone_by__username",
    ]

    ordering_fields = [
        "id",
        "ref_id",
        "status",
        "tonnage_primary",
        "tonnage_second",
        "created_at",
        "updated_at",
        "undone_at",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed_iup_ids = user_allowed_iup_ids(user)
        return qs.filter(iup_id__in=allowed_iup_ids)

    @action(detail=True, methods=["post"], url_path="undo")
    def undo(self, request, pk=None):
        merge_obj = self.get_object()

        undo_notes = request.data.get("undo_notes")

        try:
            undo_dome_merge(
                merge_obj=merge_obj,
                user=request.user if request.user.is_authenticated else None,
                notes=undo_notes,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(merge_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)