
from rest_framework.permissions import AllowAny
from master.models import MiningActivityCategories
from master.api.lookups.base import BaseLookupViewSet

class ActivityCategoriesLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = MiningActivityCategories.objects.all().order_by("code")

    # search
    search_fields = ["code__icontains", "name__icontains"]

    # fleksibel keys
    allowed_value_keys = {"id", "code"}
    allowed_label_keys = {"code", "name"}

    default_value_key = "id"
    default_label_key = "name"