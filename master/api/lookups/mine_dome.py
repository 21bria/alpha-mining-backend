from rest_framework.permissions import IsAuthenticated,AllowAny

from master.models import SourceMinesDome
from master.api.lookups.base import BaseLookupViewSet
from core.permissions import user_allowed_iup_ids


class SourceMinesDomeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = SourceMinesDome.objects.select_related("dumping", "iup").all().order_by("pile_id")

    search_fields = [
        "pile_id__icontains",
        "description__icontains",
        "dumping__dumping_point__icontains",
    ]

    allowed_value_keys = {"id", "pile_id"}
    allowed_label_keys = {"pile_id"}
    default_value_key = "id"
    default_label_key = "pile_id"

    def _get_iup_id_param(self):
        return self.request.query_params.get("iup_id") or self.request.query_params.get("iup")

    def _get_category_param(self):
        return (
            self.request.query_params.get("category")
            or self.request.query_params.get("cat")
        )

    def _get_dumping_id_param(self):
        return (
            self.request.query_params.get("dumping_id")
            or self.request.query_params.get("dumping")
        )

    def _get_dumping_name_param(self):
        return (
            self.request.query_params.get("dumping_name")
            or self.request.query_params.get("dumping_point")
            or self.request.query_params.get("sampling_area")
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
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self._get_iup_id_param()
        category = self._get_category_param()
        dumping_id = self._get_dumping_id_param()
        dumping_name = self._get_dumping_name_param()

        if category:
            qs = qs.filter(category__iexact=category.strip())

        if dumping_id:
            qs = qs.filter(dumping_id=dumping_id)

        if dumping_name:
            qs = qs.filter(dumping__dumping_point__iexact=dumping_name.strip())

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs