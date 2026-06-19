from rest_framework import serializers
from rest_framework.permissions import AllowAny
from django.db.models import Q
from master.models import SampleType
from master.api.lookups.base import BaseLookupViewSet


def parse_bool(value):
    if value in [None, ""]:
        return None

    return str(value).strip().lower() in ["true", "1", "yes", "y"]


class SampleTypeLookupSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source="id", read_only=True)
    label = serializers.CharField(source="type_sample", read_only=True)

    class Meta:
        model = SampleType
        fields = [
            "id",
            "value",
            "label",
            "type_sample",
            "description",
            "is_production",
            "is_geology",
            "is_selling",
            "is_monitoring",
        ]


class SampleTypeLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    serializer_class = SampleTypeLookupSerializer
    queryset = SampleType.objects.all().order_by("type_sample")

    search_fields = [
        "type_sample__icontains",
        "description__icontains",
    ]

    allowed_value_keys = {"id", "type_sample"}
    allowed_label_keys = {"type_sample"}
    default_value_key = "id"
    default_label_key = "type_sample"


    def get_queryset(self):
        qs = super().get_queryset()

        raw_usages = self.request.query_params.getlist("usage")

        items = []
        for raw in raw_usages:
            items += str(raw).split(",")

        usages = [x.strip().lower() for x in items if x.strip()]

        if usages:
            cond = Q()

            if "production" in usages:
                cond |= Q(is_production=True)

            if "geology" in usages:
                cond |= Q(is_geology=True)

            if "selling" in usages:
                cond |= Q(is_selling=True)

            if "monitoring" in usages:
                cond |= Q(is_monitoring=True)

            if cond:
                qs = qs.filter(cond)

            return qs

        is_production = parse_bool(self.request.query_params.get("is_production"))
        is_geology = parse_bool(self.request.query_params.get("is_geology"))
        is_selling = parse_bool(self.request.query_params.get("is_selling"))
        is_monitoring = parse_bool(self.request.query_params.get("is_monitoring"))

        if is_production is not None:
            qs = qs.filter(is_production=is_production)

        if is_geology is not None:
            qs = qs.filter(is_geology=is_geology)

        if is_selling is not None:
            qs = qs.filter(is_selling=is_selling)

        if is_monitoring is not None:
            qs = qs.filter(is_monitoring=is_monitoring)

        return qs