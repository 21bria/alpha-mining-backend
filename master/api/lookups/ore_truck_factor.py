from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

from master.models import OreTruckFactor
from master.api.lookups.base import BaseLookupViewSet
from core.permissions import user_allowed_iup_ids

class OreTruckFactorLookupViewSet(BaseLookupViewSet):
    permission_classes = [IsAuthenticated]
    queryset = (
        OreTruckFactor.objects
        .select_related("material", "iup")
        .all()
        .order_by("type_tf")
    )

    search_fields = [
        "type_tf__icontains",
        "material__name__icontains",
    ]

    allowed_value_keys = {"id", "type_tf", "material_id", "ton"}
    allowed_label_keys = {"type_tf", "ton"}
    default_value_key = "type_tf"
    default_label_key = "type_tf"

    def _get_iup_id_param(self):
        return (
            self.request.query_params.get("iup_id")
            or self.request.query_params.get("iup")
        )

    def _get_material_id_param(self):
        return (
            self.request.query_params.get("material_id")
            or self.request.query_params.get("material")
        )

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
        qs = super().get_queryset().filter(status=True)
        user = self.request.user

        iup_id = self._get_iup_id_param()
        material_id = self._get_material_id_param()

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            if iup_id:
                qs = qs.filter(iup_id=iup_id)
            if material_id:
                qs = qs.filter(material_id=material_id)
            return qs

        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)

            if not iup_id:
                return qs.none()

            qs = qs.filter(iup_id=iup_id)

            if material_id:
                qs = qs.filter(material_id=material_id)

            return qs

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        if material_id:
            qs = qs.filter(material_id=material_id)

        return qs