import django_filters
from django_filters import rest_framework as filters
from selling.models import SellingBargingTemporaryView

class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class SellingFilter(filters.FilterSet):

    # frontend kirim ...
    material = CharInFilter(field_name="material", lookup_expr="in") 

    stockpile = filters.CharFilter(field_name="stockpile", lookup_expr="iexact")
    dome = filters.CharFilter(field_name="dome", lookup_expr="iexact")

    barge_code = filters.CharFilter(field_name="barge_code", lookup_expr="iexact")
    code_lot   = filters.CharFilter(field_name="code_lot", lookup_expr="iexact")

    date_hauling_from = filters.DateFilter(field_name="date_hauling", lookup_expr="gte")
    date_hauling_to = filters.DateFilter(field_name="date_hauling", lookup_expr="lte")

    class Meta:
        model = SellingBargingTemporaryView
        fields = []