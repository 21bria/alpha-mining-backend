import django_filters
from django_filters import rest_framework as filters
from geology.models import SamplesDomeView

class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class SamplesFilter(filters.FilterSet):
    sampling_point = filters.CharFilter(field_name="sampling_point", lookup_expr="iexact")

    date_from = filters.DateFilter(field_name="date_sample", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date_sample", lookup_expr="lte")

    class Meta:
        model = SamplesDomeView
        fields = []

    def filter_queryset(self, queryset):
        sampling_point = self.form.cleaned_data.get("sampling_point")

        # Jika dome dipilih -> abaikan tanggal
        if sampling_point and sampling_point != "all":
            return queryset.filter(sampling_point__iexact=sampling_point)
        
        # Jika all / kosong -> pakai range tanggal
        date_from = self.form.cleaned_data.get("date_from")
        date_to = self.form.cleaned_data.get("date_to")

        if date_from:
            queryset = queryset.filter(date_sample__gte=date_from)

        if date_to:
            queryset = queryset.filter(date_sample__lte=date_to)

        return queryset