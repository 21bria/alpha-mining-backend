from rest_framework import serializers
from mining.models import planBarging

class planBargingSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    class Meta:
        model = planBarging
        fields = [
            "id",
            "code",
            "iup", "iup_code", "iup_name",
            "date_plan",
            "category",
            "vendor_code",
            "lim",
            "sap",
            "user",
        ] 
        read_only_fields = ["user"]
        

 