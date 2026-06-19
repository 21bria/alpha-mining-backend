from rest_framework import serializers
from geology.models import QualityConfig


from rest_framework import serializers
from geology.models import QualityConfig


class QualityConfigSerializer(serializers.ModelSerializer):

    material_name = serializers.CharField(
        source="material.name",
        read_only=True
    )

    selling_sample_type_name = serializers.CharField(
        source="selling_sample_type.type_sample",
        read_only=True
    )

    monitoring_sample_type_name = serializers.CharField(
        source="monitoring_sample_type.type_sample",
        read_only=True
    )

    class Meta:
        model = QualityConfig
        fields = [
            "id",
            "name",
            "adjust_sale",

            "material",
            "material_name",

            "selling_sample_type",
            "selling_sample_type_name",

            "monitoring_sample_type",
            "monitoring_sample_type_name",

            "is_active",
        ]
        
    def validate_adjust_sale(self, value):
        value = value.strip().upper()

        qs = QualityConfig.objects.filter(
            adjust_sale__iexact=value
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Adjust sale sudah ada."
            )

        return value