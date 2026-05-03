from rest_framework.permissions import AllowAny
from master.models import MiningActivity
from master.api.lookups.base import BaseLookupViewSet


class ActivityLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = (
        MiningActivity.objects
        .select_related("status")
        .all()
        .order_by("code")
    )

    search_fields = [
        "code__icontains",
        "name__icontains",
        "status__code__icontains",
        "status__name__icontains",
    ]

    allowed_value_keys = {"id", "code"}
    allowed_label_keys = {"code", "name"}

    default_value_key = "id"
    default_label_key = "name"

    def get_queryset(self):
        qs = super().get_queryset()

        status_id = self.request.query_params.get("status")
        if status_id:
            qs = qs.filter(status_id=status_id)

        return qs