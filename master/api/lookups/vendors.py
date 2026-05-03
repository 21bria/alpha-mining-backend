from rest_framework.permissions import IsAuthenticated,AllowAny
from master.models import Vendors
from master.api.lookups.base import BaseLookupViewSet

class VendorsLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = Vendors.objects.all().order_by("vendor_name")

    search_fields = ["vendor_name__icontains", "description__icontains"]

    allowed_value_keys = {"id", "vendor_name", "code"}
    allowed_label_keys = {"code", "vendor_name"}

    default_value_key = "id"
    default_label_key = "vendor_name"
    