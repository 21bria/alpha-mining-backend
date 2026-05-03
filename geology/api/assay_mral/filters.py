import django_filters
from django_filters import rest_framework as filters
from geology.models import AssayMral

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class AssayMralFilter(filters.FilterSet):

    release_date_from = filters.DateFilter(field_name="release_date", lookup_expr="gte")
    release_date_to = filters.DateFilter(field_name="release_date", lookup_expr="lte")

    class Meta:
        model = AssayMral
        fields = []