import django_filters
from django_filters import rest_framework as filters
from geology.models import OreProductionsView

class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class ProductionsFilter(filters.FilterSet):

    material = CharInFilter(field_name="nama_material", lookup_expr="in") 

    prospect_area  = filters.CharFilter(field_name="prospect_area", lookup_expr="iexact")
    sampling_area  = filters.CharFilter(field_name="stockpile", lookup_expr="iexact")
    pile_id        = filters.CharFilter(field_name="pile_id", lookup_expr="iexact")

    tgl_production_from = filters.DateFilter(field_name="tgl_production", lookup_expr="gte")
    tgl_production_to = filters.DateFilter(field_name="tgl_production", lookup_expr="lte")

    class Meta:
        model = OreProductionsView
        fields = []