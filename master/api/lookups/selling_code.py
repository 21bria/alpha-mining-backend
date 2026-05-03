from rest_framework.permissions import IsAuthenticated,AllowAny
from master.models import SellingCode
from master.api.lookups.base import BaseLookupViewSet

class SellingCodeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = SellingCode.objects.all().order_by("code")

    search_fields = ["code__icontains", "description__icontains"]

    allowed_value_keys = {"id", "code"}
    allowed_label_keys = {"code"}
    default_value_key = "id"
    default_label_key = "code"

    def get_queryset(self):
        qs = super().get_queryset()

        user = self.request.user

        # FILTER TYPE
        type_param = self.request.query_params.get("type")
        if type_param:
            qs = qs.filter(type__iexact=type_param)

        # 1) Sistem/superuser: boleh semua
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        # 2) Ambil iup_id dari query param
        iup_id = self.request.query_params.get("iup_id")

        # Site user wajib iup
        if getattr(user, "is_site_user", False):
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        # 3) Management/global viewer
        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs