from rest_framework.permissions import AllowAny
from master.models import SourcePitDome
from master.api.lookups.base import BaseLookupViewSet
from core.permissions import user_allowed_iup_ids


class SourcePitDomeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]

    queryset = (
        SourcePitDome.objects
        .select_related(
            "loading_point",
            "loading_point__iup",
        )
        .all()
        .order_by("dome")
    )

    search_fields = [
        "dome__icontains",
        "description__icontains",
        "loading_point__loading_point__icontains",
    ]

    allowed_value_keys = {"id", "dome"}
    allowed_label_keys = {"dome"}
    default_value_key = "id"
    default_label_key = "dome"

    def _get_iup_id_param(self):
        return (
            self.request.query_params.get("iup_id")
            or self.request.query_params.get("iup")
        )

    def _get_dome_type_param(self):
        return (
            self.request.query_params.get("dome_type")
            or self.request.query_params.get("type")
        )

    def _get_loading_point_id_param(self):
        return (
            self.request.query_params.get("loading_point")
            or self.request.query_params.get("loading_point_id")
            or self.request.query_params.get("id_loading")
        )

    def _get_loading_point_name_param(self):
        return (
            self.request.query_params.get("loading_point_name")
            or self.request.query_params.get("loading_point")
        )

    def _get_active_iup_id_for_user(self, user):
        active = (
            getattr(user, "active_iup_id", None)
            or getattr(user, "iup_id", None)
        )

        if active:
            return str(active)

        allowed = user_allowed_iup_ids(user)

        if not allowed:
            return None

        allowed_list = list(allowed)
        return str(allowed_list[0]) if allowed_list else None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self._get_iup_id_param()
        dome_type = self._get_dome_type_param()

        loading_point_id = self._get_loading_point_id_param()
        loading_point_name = self.request.query_params.get("loading_point_name")

        if dome_type:
            qs = qs.filter(dome_type__iexact=dome_type.strip())

        if loading_point_id:
            qs = qs.filter(loading_point_id=loading_point_id)

        if loading_point_name:
            qs = qs.filter(
                loading_point__loading_point__iexact=loading_point_name.strip()
            )

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            if iup_id:
                qs = qs.filter(loading_point__iup_id=iup_id)
            return qs

        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)

            if not iup_id:
                return qs.none()

            return qs.filter(loading_point__iup_id=iup_id)

        if iup_id:
            qs = qs.filter(loading_point__iup_id=iup_id)

        return qs