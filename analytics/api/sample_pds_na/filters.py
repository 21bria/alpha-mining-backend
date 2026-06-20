import django_filters
from django_filters import rest_framework as filters
from geology.models import SamplesPdsNaView

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class SamplesFilter(filters.FilterSet):
    sampling_point = filters.CharFilter(
        field_name="sampling_point",
        lookup_expr="iexact"
    )

    date_from = filters.DateFilter(
        field_name="date_sample",
        lookup_expr="gte"
    )
    date_to = filters.DateFilter(
        field_name="date_sample",
        lookup_expr="lte"
    )

    class Meta:
        model = SamplesPdsNaView
        fields = []

    def filter_queryset(self, queryset):
        sampling_point = self.form.cleaned_data.get("sampling_point")
        date_from = self.form.cleaned_data.get("date_from")
        date_to = self.form.cleaned_data.get("date_to")

        # Filter dome kalau dipilih
        if sampling_point and sampling_point.lower() != "all":
            queryset = queryset.filter(
                sampling_point__iexact=sampling_point
            )

        # Filter tanggal hanya kalau dikirim
        if date_from:
            queryset = queryset.filter(date_sample__gte=date_from)

        if date_to:
            queryset = queryset.filter(date_sample__lte=date_to)

        return queryset