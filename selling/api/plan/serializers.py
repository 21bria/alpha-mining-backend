from rest_framework import serializers
from selling.models import BargingPlan


class BargingPlanSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)
    tonnage_plan = serializers.SerializerMethodField()

    class Meta:
        model = BargingPlan
        fields = [
            "id",
            "code",
            "iup_id",
            "iup_code",
            "iup_name",
            "plan_date",
            "tugboat_name",
            "barge_code",
            "tonnage_plan",
            "no_plan",
            "description",
            "id_user",
            "created_at",
            "updated_at",
        ]

    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_tonnage_plan(self, obj):
        return self._fmt_decimal(obj.tonnage_plan)