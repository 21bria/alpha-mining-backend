from rest_framework import serializers
from django.utils import timezone
from mining.models import planProductions

class planProductionsSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    class Meta:
        model = planProductions
        fields = [
            "id",
            "iup", "iup_code", "iup_name",

            "date_plan",
            "category",
            "sources",

            "vendors",
            "topsoil",
            "ob",
            "waste",
            "lim",
            "sap",
            "quarry",
            "ballast",
            "biomass",
            "user"
        ]
        read_only_fields = ["user"]
        

 