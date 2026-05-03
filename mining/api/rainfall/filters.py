import django_filters
from django_filters import rest_framework as filters
from mining.models import Rainfall


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class RainfallFilter(filters.FilterSet):

    point_id    = CharInFilter(field_name="point_id", lookup_expr="in") 
    
    date_start  = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_end    = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Rainfall
        fields = []