
from rest_framework.permissions import AllowAny
from mining.models import RainfallPoint
from master.api.lookups.base import BaseLookupViewSet

class RanfallPointsLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = RainfallPoint.objects.all().order_by("name")

    # search
    search_fields = ["name__icontains", "description__icontains"]

    # fleksibel keys
    allowed_value_keys = {"id", "name"}
    allowed_label_keys = {"name", "name"}

    default_value_key = "id"
    default_label_key = "name"