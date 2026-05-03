from rest_framework import serializers
from mining.models import FuelConsumptionView

class FuelConsumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelConsumptionView
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",

            "date",
            "shift",
            "unit",
            "category",
            "hours_metre",
            "drivers",
            "charging_time",
            "volume",
            "storage",
            "operator",
            "code",
            "iup_id",
            "iup_code",
            "iup_name",
            "user_id",
            "username",
            "created_at"
        ]
