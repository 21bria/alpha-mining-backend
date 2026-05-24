import django_filters
from django_filters import rest_framework as filters
from analytics.models_bod_weekly import BodWeeklyReport

class NumberFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class WeeklyFilter(filters.FilterSet):
    iup_id = NumberFilter(field_name="iup_id", lookup_expr="in")

    period_start = filters.DateFilter(field_name="period_start", lookup_expr="gte")
    period_end = filters.DateFilter(field_name="period_end", lookup_expr="lte")

    class Meta:
        model = BodWeeklyReport
        fields = []