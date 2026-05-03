from rest_framework.permissions import IsAuthenticated,AllowAny
from master.models import SampleType
from master.api.lookups.base import BaseLookupViewSet

class SampleTypeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = SampleType.objects.all().order_by("type_sample")

    search_fields = [
        "type_sample__icontains",
        "description__icontains",
    ]

    allowed_value_keys = {"id", "type_sample"}
    allowed_label_keys = {"type_sample"}
    default_value_key = "id"
    default_label_key = "type_sample"

    def _get_category_param(self):
        return (
            self.request.query_params.get("category")
            or self.request.query_params.get("cat")
        )

    def get_queryset(self):
        qs = super().get_queryset()

        category = self._get_category_param()

        if category:
            qs = qs.filter(category__iexact=category.strip())

        return qs