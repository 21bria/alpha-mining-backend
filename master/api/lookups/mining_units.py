from rest_framework.permissions import AllowAny
from master.models import MineUnits
from master.api.lookups.base import BaseLookupViewSet

class MineUnitsLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = MineUnits.objects.all().order_by("unit_code")
    search_fields = ["unit_code__icontains", "unit_vendor__icontains"]

    allowed_value_keys = {"id", "unit_vendor"}
    allowed_label_keys = {"unit_vendor", "unit_vendor"}
    default_value_key = "id"
    default_label_key = "unit_vendor"

    def get_queryset(self):
        qs = super().get_queryset()

        u = self.request.user
        role = getattr(u, "role", None)

        # SYSTEM/MANAGEMENT => all
        if u.is_superuser or role in ("SYSTEM", "MANAGEMENT"):
            return qs

        # SITE_USER => filter allowed_iup_ids
        allowed = getattr(u, "allowed_iup_ids", []) or []
        return qs.filter(id__in=allowed)
    