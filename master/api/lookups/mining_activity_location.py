from rest_framework.permissions import AllowAny
from master.models import MiningActivityLocation
from master.api.lookups.base import BaseLookupViewSet


class ActivityLocationLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = MiningActivityLocation.objects.all().order_by("name")

    search_fields = [
        "name__icontains",
        "description__icontains",
    ]

    allowed_value_keys = {"id", "name"}
    allowed_label_keys = {"name"}

    default_value_key = "id"
    default_label_key = "name"