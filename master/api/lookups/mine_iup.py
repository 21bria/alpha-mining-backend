
from rest_framework.permissions import AllowAny
from master.models import MineIUP
from master.api.lookups.base import BaseLookupViewSet
from rest_framework import serializers

class MineIUPLookupSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source="id", read_only=True)
    label = serializers.CharField(source="iup_code", read_only=True)

    class Meta:
        model = MineIUP
        fields = ["id", "value", "label", "iup_code", "iup_name"]

class MineIUPLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    serializer_class = MineIUPLookupSerializer
    queryset = MineIUP.objects.all().order_by("iup_name")
    search_fields = ["iup_code__icontains", "iup_name__icontains"]

    allowed_value_keys = {"id", "iup_code"}
    allowed_label_keys = {"iup_code", "iup_name"}
    default_value_key = "id"
    default_label_key = "iup_code"

    def get_queryset(self):
        qs = super().get_queryset()

        u = self.request.user
        role = getattr(u, "role", None)

        if u.is_superuser or role in ("SYSTEM", "MANAGEMENT", "GLOBAL_VIEWER"):
            return qs

        allowed = getattr(u, "allowed_iup_ids", []) or []

        if isinstance(allowed, str):
            try:
                allowed = json.loads(allowed)
            except Exception:
                allowed = []

        return qs.filter(id__in=allowed)
