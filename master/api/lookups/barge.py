
from rest_framework.permissions import AllowAny
from master.models import BargeUnits
from master.api.lookups.base import BaseLookupViewSet

class BargeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = BargeUnits.objects.all().order_by("barge_name")

    # search
    search_fields = ["barge_name__icontains", "description__icontains"]

    # fleksibel keys
    allowed_value_keys = {"id", "barge_code"}
    allowed_label_keys = {"barge_code", "barge_name"}

    default_value_key = "id"
    default_label_key = "barge_code"