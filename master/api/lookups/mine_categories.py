from rest_framework.permissions import IsAuthenticated
from master.api.lookups.base import BaseLookupViewSet

from rest_framework.permissions import IsAuthenticated
from master.models import MineCategory
from master.api.lookups.base import BaseLookupViewSet

from core.permissions import user_allowed_iup_ids  # pastikan ini ada

class MineCategoryLookupViewSet(BaseLookupViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MineCategory.objects.all().order_by("category")

    search_fields = ["category__icontains", "description__icontains"]

    allowed_value_keys = {"id", "category"}
    allowed_label_keys = {"category"}
    default_value_key = "id"
    default_label_key = "category"
