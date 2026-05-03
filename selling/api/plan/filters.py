import django_filters
from django_filters import rest_framework as filters
from selling.models import BargingPlan

class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class SellingFilter(filters.FilterSet):
    # frontend kirim ...
    barge_code = CharInFilter(field_name="barge_code", lookup_expr="in") 

    date_start = filters.DateFilter(field_name="plan_date", lookup_expr="gte")
    date_end = filters.DateFilter(field_name="plan_date", lookup_expr="lte")

    class Meta:
        model = BargingPlan
        fields = []