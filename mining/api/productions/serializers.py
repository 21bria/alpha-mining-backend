from rest_framework import serializers
from mining.models import mineProductionsView

class ProductionsSerializer(serializers.ModelSerializer):
    tonnage = serializers.SerializerMethodField()
    class Meta:
        model = mineProductionsView
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",

            "category_mine",
            "is_ore",
            "is_production",
            
            "date_production",
            "shift",

            "vendors",
            "loader",
            "bucket",
            "hauler",

            "hauler_class",
            "sources_area",
            "loading_point",
            "dumping_point",
            "dome_id",
            "time_loading",
            "time_dumping",
            "mine_block",
            "rl",
            "nama_material",
            "ritase",
            "bcm",
            "tonnage",
            "remarks",
            "t_load",
            "hauler_type",
            "direct",
            "created_at",
            "user_id",
            "username"
        ]
        
    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_tonnage(self, obj):
        return self._fmt_decimal(obj.tonnage)