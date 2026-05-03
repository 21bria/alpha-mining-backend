import django_filters
from django_filters import rest_framework as filters
from mining.models import FuelConsumptionView

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class FuelFilter(filters.FilterSet):

    code = filters.CharFilter(field_name="code", lookup_expr="iexact")
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")

    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = FuelConsumptionView
        fields = []