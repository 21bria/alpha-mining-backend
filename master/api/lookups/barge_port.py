
from rest_framework.permissions import AllowAny
from master.models import BargeUnits
from master.api.lookups.base import BaseLookupViewSet
from master.models.barge import BargePort

class BargePortLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = BargePort.objects.all().order_by("port_name")

    # search
    search_fields = ["port_name__icontains", "description__icontains"]

    # fleksibel keys
    allowed_value_keys = {"id", "port_name"}
    allowed_label_keys = {"port_name", "description"}

    default_value_key = "id"
    default_label_key = "port_name"