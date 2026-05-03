import django_filters
from django_filters import rest_framework as filters
from geology.models import listWaybills

class WaybillFilter(filters.FilterSet):


    mral_order  = filters.CharFilter(field_name="mral_order", lookup_expr="iexact")
    roa_order   = filters.CharFilter(field_name="roa_order", lookup_expr="iexact")

    date_start = filters.DateFilter(field_name="tgl_deliver", lookup_expr="gte")
    date_end   = filters.DateFilter(field_name="tgl_deliver", lookup_expr="lte")

    class Meta:
        model = listWaybills
        fields = []