import django_filters
from django_filters import rest_framework as filters
from mining.models import Weather


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class WeatherFilter(filters.FilterSet):

    # frontend kirim ...
    category = CharInFilter(field_name="category", lookup_expr="in") 

    date_start = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_end   = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Weather
        fields = []