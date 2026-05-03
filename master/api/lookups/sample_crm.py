from rest_framework.permissions import AllowAny
from geology.models.geology_sample_crm_certified import SampleCrmCertified
from master.api.lookups.base import BaseLookupViewSet

# class CRMCertificateLookupViewSet(BaseLookupViewSet):
#     permission_classes = [AllowAny]
#     queryset = SampleCrmCertified.objects.all().order_by("oreas_name")

#     search_fields = ["oreas_name__icontains"]

#     allowed_value_keys = {"id", "oreas_name"}
#     allowed_label_keys = {"oreas_name"}

#     default_value_key = "id"
#     default_label_key = "name"

#     def get_queryset(self):
#         qs = super().get_queryset()
#         return qs

class CRMCertificateLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    queryset = SampleCrmCertified.objects.all().order_by("oreas_name")

    search_fields = ["oreas_name__icontains"]

    allowed_value_keys = {"id", "oreas_name"}
    allowed_label_keys = {"oreas_name"}

    default_value_key = "name"
    default_label_key = "name"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs