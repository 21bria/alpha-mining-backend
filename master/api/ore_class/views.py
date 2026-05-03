from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from master.models import OreClass
from .serializers import OreClassSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet
from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)


class OreClassViewSet(MasterBaseViewSet):
    queryset = OreClass.objects.select_related("iup", "material", "user").all().order_by("ore_class")
    serializer_class = OreClassSerializer

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
        "ore_class",
        "iup__iup_code",
        "iup__iup_name",
        "material__name",
        "material__code",
    ]

    ordering_fields = [
        "id",
        "code",
        "ore_class",
        "status",
        "ni_min",
        "ni_max",
        "mgo_min",
        "mgo_max",
        "fe_min",
        "fe_max",
        "created_at",
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

        # system / superuser
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        # site user: default ke active_iup kalau param kosong
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs