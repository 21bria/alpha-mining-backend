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

    def _get_category_params(self):
        categories = self.request.query_params.getlist("category")

        if categories:
            return [
                c.strip()
                for c in categories
                if c and c.strip()
            ]

        raw = (
            self.request.query_params.get("category")
            or self.request.query_params.get("cat")
        )

        if not raw:
            return []

        return [
            c.strip()
            for c in raw.split(",")
            if c and c.strip()
        ]

    def get_queryset(self):
        qs = super().get_queryset()

        categories = self._get_category_params()

        if categories:
            qs = qs.filter(category__in=categories)

        return qs