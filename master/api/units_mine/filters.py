import django_filters
from django_filters import rest_framework as filters
from master.models import MineUnits

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class UnitsFilter(filters.FilterSet):

    # frontend kirim ...
    id_category = NumberInFilter(field_name="id_category", lookup_expr="in") 

    class Meta:
        model = MineUnits
        fields = []