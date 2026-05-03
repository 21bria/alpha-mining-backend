from django_filters import rest_framework as filters
from mining.models import HmUnit


class acitvityFilter(filters.FilterSet):

    date_start = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_end = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = HmUnit
        fields = []