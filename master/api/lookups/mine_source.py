from rest_framework.permissions import IsAuthenticated
from master.models import SourceMines
from master.api.lookups.base import BaseLookupViewSet

from rest_framework.permissions import IsAuthenticated
from master.models import SourceMines
from master.api.lookups.base import BaseLookupViewSet

from core.permissions import user_allowed_iup_ids  # pastikan ini ada

class SourceMinesLookupViewSet(BaseLookupViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SourceMines.objects.all().order_by("sources_area")

    search_fields = ["sources_area__icontains", "description__icontains"]

    allowed_value_keys = {"id", "sources_area"}
    allowed_label_keys = {"sources_area"}
    default_value_key = "id"
    default_label_key = "sources_area"

    def _get_iup_id_param(self):
        return self.request.query_params.get("iup_id") or self.request.query_params.get("iup")

    def _get_active_iup_id_for_user(self, user):
        active = getattr(user, "active_iup_id", None) or getattr(user, "iup_id", None)
        if active:
            return str(active)

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return None

        # allowed bisa list / set -> aman untuk dua-duanya
        try:
            return str(next(iter(allowed)))
        except TypeError:
            # fallback kalau aneh
            allowed_list = list(allowed)
            return str(allowed_list[0]) if allowed_list else None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self._get_iup_id_param()

        # SYSTEM/superuser: boleh semua, tapi kalau ada iup_id tetap filter
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        # SITE_USER: auto pakai iup aktif kalau param tidak dikirim
        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        # MANAGEMENT / GLOBAL_VIEWER: kalau dikirim iup_id, filter
        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs