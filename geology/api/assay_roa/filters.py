import django_filters
from django_filters import rest_framework as filters
from geology.models import AssayRoa

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class AssayRoaFilter(filters.FilterSet):

    date_start = filters.DateFilter(field_name="release_date", lookup_expr="gte")
    date_end   = filters.DateFilter(field_name="release_date", lookup_expr="lte")

    class Meta:
        model = AssayRoa
        fields = []