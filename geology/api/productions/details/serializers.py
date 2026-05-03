from rest_framework import serializers
import re
from geology.models import DetailsRoa

class ProductionsSerializer(serializers.ModelSerializer):
    tonnage = serializers.SerializerMethodField()

    class Meta:
        model = DetailsRoa
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",
            "category",
            "tgl_production",
            "shift",

            "prospect_area",
            "mine_block",
            "from_rl",
            "to_rl",

            "nama_material",
            "ore_class",
            "ni_grade",
            "grade_control",
            "unit_truck",
            "stockpile",
            "pile_id",
            "batch_code",
            "increment",
            "batch_status",
            "ritase",
            "tonnage",
            "pile_status",
            "remarks",
            "sample_number",
            "roa_ni",
            "direct",
            # "created_at",
            "user_id",
            "username"
        ]
        
    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_tonnage(self, obj):
        return self._fmt_decimal(obj.tonnage)
