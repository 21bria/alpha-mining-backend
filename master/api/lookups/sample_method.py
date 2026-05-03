from rest_framework.permissions import AllowAny

from master.models import SampleMethod
from master.api.lookups.base import BaseLookupViewSet

class SampleMethodLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = SampleMethod.objects.select_related("sample_type").all().order_by("sample_method")

    search_fields = [
        "sample_method__icontains",
        "description__icontains",
        "sample_type__type_sample__icontains",
    ]

    allowed_value_keys = {"id", "sample_method"}
    allowed_label_keys = {"sample_method"}
    default_value_key = "id"
    default_label_key = "sample_method"

    def _get_sample_type_id_param(self):
        return (
            self.request.query_params.get("sample_type_id")
            or self.request.query_params.get("type_id")
            or self.request.query_params.get("sample_type")
        )

    def _get_sample_type_name_param(self):
        return (
            self.request.query_params.get("sample_type_name")
            or self.request.query_params.get("type_sample")
            or self.request.query_params.get("type_name")
        )

    def _get_category_param(self):
        return self.request.query_params.get("category") or self.request.query_params.get("cat")

    def get_queryset(self):
        qs = super().get_queryset()

        sample_type_id = self._get_sample_type_id_param()
        sample_type_name = self._get_sample_type_name_param()
        category = self._get_category_param()

        if sample_type_id:
            qs = qs.filter(sample_type_id=sample_type_id)

        if sample_type_name:
            qs = qs.filter(sample_type__type_sample__iexact=sample_type_name.strip())

        if category:
            qs = qs.filter(sample_type__category__iexact=category.strip())

        return qs