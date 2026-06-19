from rest_framework import serializers
from rest_framework.permissions import AllowAny
from master.models import Material
from master.api.lookups.base import BaseLookupViewSet


class MaterialLookupSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source="id", read_only=True)
    label = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Material
        fields = [
            "id",
            "value",
            "label",
            "name",
            "description",
            "is_ore",
            "is_production",
            "sale_adjust",
        ]


class MaterialLookupViewSet(BaseLookupViewSet):
    permission_classes = [AllowAny]
    serializer_class = MaterialLookupSerializer
    queryset = Material.objects.all().order_by("name")

    search_fields = ["name__icontains", "description__icontains"]

    allowed_value_keys = {"id", "name"}
    allowed_label_keys = {"name"}

    default_value_key = "id"
    default_label_key = "name"

    def get_queryset(self):
        qs = super().get_queryset()

        is_ore = self.request.query_params.get("is_ore")
        is_production = self.request.query_params.get("is_production")

        if is_ore is not None:
            qs = qs.filter(is_ore=str(is_ore).lower() in ["true", "1", "yes"])

        if is_production is not None:
            qs = qs.filter(is_production=str(is_production).lower() in ["true", "1", "yes"])

        return qs