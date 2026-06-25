from rest_framework.permissions import IsAuthenticated,AllowAny
from django.db.models import Q
from master.models import SellingCode
from master.api.lookups.base import BaseLookupViewSet


class SellingCodeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = SellingCode.objects.all().order_by("code")

    search_fields = []
    allowed_value_keys = {"id", "code"}
    allowed_label_keys = {"code"}
    default_value_key = "id"
    default_label_key = "code"

    def get_queryset(self):
        qs = SellingCode.objects.all().order_by("code")
        user = self.request.user

        q = self.request.query_params.get("q")
        if q:
            q = q.strip()
            qs = qs.filter(
                Q(code__icontains=q) |
                Q(description__icontains=q)
            )

        type_param = self.request.query_params.get("type")
        if type_param:
            qs = qs.filter(type__iexact=type_param)

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        iup_id = self.request.query_params.get("iup_id")

        if not iup_id:
            iup_id = getattr(user, "active_iup_id", None) or getattr(user, "default_iup_id", None)

        if getattr(user, "is_site_user", False):
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs