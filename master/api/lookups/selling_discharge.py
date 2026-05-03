from rest_framework.permissions import IsAuthenticated,AllowAny
from master.models import StockFactories
from master.api.lookups.base import BaseLookupViewSet


class DischargeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = StockFactories.objects.all().order_by("factory_stock")

    search_fields = ["factory_stock__icontains", "description__icontains"]

    allowed_value_keys = {"id", "factory_stock"}
    allowed_label_keys = {"factory_stock", "description"}
    default_value_key = "id"
    default_label_key = "factory_stock"
