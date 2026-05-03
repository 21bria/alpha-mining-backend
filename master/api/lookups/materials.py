from rest_framework.permissions import AllowAny
from master.models import Material
from master.api.lookups.base import BaseLookupViewSet


class MaterialLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = Material.objects.all().order_by("name")

    search_fields = ["name__icontains", "description__icontains"]

    allowed_value_keys = {"id", "name"}
    allowed_label_keys = {"name"}

    default_value_key = "id"
    default_label_key = "name"

    def get_queryset(self):
        qs = super().get_queryset()

        categories = (
            self.request.query_params.get("categories")
            or self.request.query_params.get("category")
        )

        if categories:
            qs = qs.filter(categories__iexact=categories)

        return qs