import django_filters
from django_filters import rest_framework as filters
from selling.models import SellingDetailsBargingView

class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class SellingFilter(filters.FilterSet):

    # frontend kirim ...
    material = CharInFilter(field_name="material", lookup_expr="in") 

    date_hauling_from = filters.DateFilter(field_name="date_hauling", lookup_expr="gte")
    date_hauling_to = filters.DateFilter(field_name="date_hauling", lookup_expr="lte")

    class Meta:
        model = SellingDetailsBargingView
        fields = []