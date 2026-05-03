import django_filters
from django_filters import rest_framework as filters
from geology.models import sampleCrmMralView,sampleCrmRoaView

class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class MralFilter(filters.FilterSet):

    oraes = CharInFilter(field_name="oreas_name", lookup_expr="in") 

    start_date = filters.DateFilter(field_name="release_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="release_date", lookup_expr="lte")

    class Meta:
        model = sampleCrmMralView
        fields = []

class RoaFilter(filters.FilterSet):

    oraes = CharInFilter(field_name="oreas_name", lookup_expr="in") 

    start_date = filters.DateFilter(field_name="release_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="release_date", lookup_expr="lte")

    class Meta:
        model = sampleCrmRoaView
        fields = []