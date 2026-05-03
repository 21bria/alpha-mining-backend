import django_filters
from django_filters import rest_framework as filters
from mining.models import mineProductionsView

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class ProductionsFilter(filters.FilterSet):

    # frontend kirim agreement_status=1,2,3
    # agreement_status = NumberInFilter(field_name="agreement_status_id", lookup_expr="in")

    loading_point = filters.CharFilter(field_name="loading_point", lookup_expr="iexact")
    dumping_point = filters.CharFilter(field_name="dumping_point", lookup_expr="iexact")

    date_production_from = filters.DateFilter(field_name="date_production", lookup_expr="gte")
    date_production_to = filters.DateFilter(field_name="date_production", lookup_expr="lte")

    class Meta:
        model = mineProductionsView
        fields = []