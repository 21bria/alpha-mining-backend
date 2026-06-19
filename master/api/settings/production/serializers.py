from rest_framework import serializers
from geology.models import ProductionsConfig


class ProductionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionsConfig
        fields = [
            "id",
            "key",
            "value",
            "is_active"
        ]

    def validate_name(self, value: str):
        key = value.strip()

        qs = ProductionsConfig.objects.filter(key__iexact=key)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Key sudah ada."
            )

        return key