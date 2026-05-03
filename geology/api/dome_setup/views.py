from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from geology.models import domeStatusClose, domeStatusFinish
from .close_serializers import DomeStatusCloseSerializer
from .finished_serializers import DomeStatusFinishSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet
from core.permissions import (
    RoleReadOnlyForViewer,
    user_allowed_iup_ids,
)

class DomeStatusCloseViewSet(MasterBaseViewSet):
    queryset = domeStatusClose.objects.select_related("dome", "user").all().order_by("-created_at")
    serializer_class = DomeStatusCloseSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "status_dome",
        "description",
        "cek_duplicated",
        "dome__name",
        "dome__code",
    ]

    ordering_fields = [
        "id",
        "tonnage_dome",
        "status_dome",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        dome_id = self.request.query_params.get("dome")
        if dome_id:
            qs = qs.filter(dome_id=dome_id)

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        # asumsi dome punya field iup
        return qs.filter(dome__iup_id__in=allowed)


class DomeStatusFinishViewSet(MasterBaseViewSet):
    queryset = domeStatusFinish.objects.select_related("dome", "user").all().order_by("-created_at")
    serializer_class = DomeStatusFinishSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "status_dome",
        "description",
        "cek_duplicated",
        "dome__name",
        "dome__code",
    ]

    ordering_fields = [
        "id",
        "tonnage_dome",
        "status_dome",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        dome_id = self.request.query_params.get("dome")
        if dome_id:
            qs = qs.filter(dome_id=dome_id)

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        # asumsi dome punya field iup
        return qs.filter(dome__iup_id__in=allowed)