import django_filters
from django_filters import rest_framework as filters
from mining.models import MiningActivity


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

class activityFilter(filters.FilterSet):

    status_id= CharInFilter(field_name="status_id", lookup_expr="in") 

    class Meta:
        model = MiningActivity
        fields = []