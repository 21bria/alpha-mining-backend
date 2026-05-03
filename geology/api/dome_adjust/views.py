from rest_framework import filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from geology.models import DomeAdjustment
from .serializers import DomeAdjustmentSerializer

from master.api.base import MasterBaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
)

class DomeAdjustmentViewSet(MasterBaseViewSet):
    queryset = DomeAdjustment.objects.select_related("dome", "user", "dome__iup").all().order_by("-created_at")
    serializer_class = DomeAdjustmentSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "dome__name",
        "dome__code",
        "description",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "target_total",
        "current_total",
        "scale_factor",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed_iup_ids = getattr(user, "allowed_iup_ids", None)
        if callable(allowed_iup_ids):
            allowed_iup_ids = allowed_iup_ids()

        if not allowed_iup_ids:
            from core.permissions import user_allowed_iup_ids
            allowed_iup_ids = user_allowed_iup_ids(user)

        return qs.filter(dome__iup_id__in=allowed_iup_ids)