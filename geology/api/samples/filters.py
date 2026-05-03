import django_filters
from django_filters import rest_framework as filters
from geology.models import SamplesView

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class SamplesFilter(filters.FilterSet):

    # frontend kirim agreement_status=1,2,3
    # agreement_status = NumberInFilter(field_name="agreement_status_id", lookup_expr="in")

    sampling_area = filters.CharFilter(field_name="sampling_area", lookup_expr="iexact")
    sampling_point = filters.CharFilter(field_name="sampling_point", lookup_expr="iexact")

    date_sample_from = filters.DateFilter(field_name="date_sample", lookup_expr="gte")
    date_sample_to = filters.DateFilter(field_name="date_sample", lookup_expr="lte")

    class Meta:
        model = SamplesView
        fields = []