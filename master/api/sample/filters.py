import django_filters
from django_filters import rest_framework as filters
from master.models import SampleMethod

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class MathodFilter(filters.FilterSet):

    # frontend kirim ...
    sample_type = NumberInFilter(field_name="sample_type", lookup_expr="in") 

    class Meta:
        model = SampleMethod
        fields = []