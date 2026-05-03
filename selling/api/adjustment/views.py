from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from selling.models import SellingBargingAdjustment
from .serializers import SellingBargingAdjustmentSerializer

from master.api.base import MasterBaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
    user_allowed_iup_ids,
)


class SellingBargingAdjustmentViewSet(MasterBaseViewSet):
    queryset = (
        SellingBargingAdjustment.objects
        .select_related("code_lot", "user", "code_lot__iup")
        .all()
        .order_by("-created_at")
    )
    serializer_class = SellingBargingAdjustmentSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = [
        "code_lot",
        "status",
        "date_arrival",
        "date_departure",
        "code_lot__iup_id",
        "code_lot__type",
    ]

    search_fields = [
        "code_lot__code",
        "code_lot__description",
        "code_lot__type",
        "description",
        "user__username",
        "status",
        "jetty_departure",
    ]

    ordering_fields = [
        "id",
        "date_arrival",
        "date_departure",
        "ritase_ori",
        "tonnage_ori",
        "tonnage_adjust",
        "status",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self.request.query_params.get("iup_id")
        type_param = self.request.query_params.get("type")

        if iup_id:
            qs = qs.filter(code_lot__iup_id=iup_id)

        if type_param:
            qs = qs.filter(code_lot__type__iexact=type_param)

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed_iup_ids = getattr(user, "allowed_iup_ids", None)
        if callable(allowed_iup_ids):
            allowed_iup_ids = allowed_iup_ids()

        if not allowed_iup_ids:
            allowed_iup_ids = user_allowed_iup_ids(user)

        return qs.filter(code_lot__iup_id__in=allowed_iup_ids)