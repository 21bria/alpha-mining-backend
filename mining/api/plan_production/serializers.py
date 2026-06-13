from rest_framework import serializers
from mining.models import PlanProduction, PlanProductionDetail


class PlanProductionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanProductionDetail
        fields = [
            "id",
            "material_code",
            "material_name",
            "tonnage",
        ]


class planProductionSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    details = PlanProductionDetailSerializer(many=True, read_only=True)

    # optional summary untuk table lama
    total_tonnage = serializers.SerializerMethodField()

    class Meta:
        model = PlanProduction
        fields = [
            "id",
            "code",
            "iup",
            "iup_code",
            "iup_name",
            "date_plan",
            "category",
            "source_code",
            "vendor_code",
            "ref_plan",
            "details",
            "total_tonnage",
            "user",
        ]
        read_only_fields = ["user"]

    def get_total_tonnage(self, obj):
        return sum((d.tonnage or 0) for d in obj.details.all())