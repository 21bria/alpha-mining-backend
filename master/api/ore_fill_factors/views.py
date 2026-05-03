from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from master.models import OreTruckFactor
from .serializers import OreTruckFactorSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet
from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)


class OreTruckFactorViewSet(MasterBaseViewSet):
    queryset = OreTruckFactor.objects.select_related("iup", "material", "user").all().order_by("type_tf")
    serializer_class = OreTruckFactorSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "code",
        "type_tf",
        "iup__iup_code",
        "iup__iup_name",
        "material__name",
        "material__code",
    ]

    ordering_fields = [
        "id",
        "code",
        "type_tf",
        "density",
        "bcm",
        "ton",
        "status",
        "created_at",
        "updated_at",
    ]

    soft_delete_field = "is_deleted"

    def _get_iup_id_param(self):
        return self.request.query_params.get("iup_id") or self.request.query_params.get("iup")

    def _get_active_iup_id_for_user(self, user):
        active = getattr(user, "active_iup_id", None) or getattr(user, "iup_id", None)
        if active:
            return str(active)

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return None

        try:
            return str(next(iter(allowed)))
        except TypeError:
            allowed_list = list(allowed)
            return str(allowed_list[0]) if allowed_list else None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        iup_id = self._get_iup_id_param()

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs