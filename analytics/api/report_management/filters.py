import django_filters
from django_filters import rest_framework as filters

from analytics.models_report_management import ReportManagement


class NumberFilter(
    django_filters.BaseInFilter,
    django_filters.NumberFilter,
):
    pass


class ReportManagementFilter(filters.FilterSet):
    iup_id = NumberFilter(field_name="iup_id", lookup_expr="in")

    period_type = filters.CharFilter(field_name="period_type", lookup_expr="exact")

    yearly = filters.NumberFilter(field_name="yearly")
    monthly = filters.NumberFilter(field_name="monthly")
    weekly = filters.NumberFilter(field_name="weekly")

    status = filters.CharFilter(field_name="status", lookup_expr="exact")

    period_start = filters.DateFilter(field_name="period_start", lookup_expr="gte")
    period_end = filters.DateFilter(field_name="period_end", lookup_expr="lte")

    class Meta:
        model = ReportManagement
        fields = [
            "iup_id",
            "period_type",
            "yearly",
            "monthly",
            "weekly",
            "status",
            "period_start",
            "period_end",
        ]