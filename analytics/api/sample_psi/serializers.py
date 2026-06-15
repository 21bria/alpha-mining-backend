from rest_framework import serializers
from geology.models import SamplesPsiView

class SamplesPsiSerializer(serializers.ModelSerializer):

    ni_display = serializers.SerializerMethodField()
    co_display = serializers.SerializerMethodField()
    al2o3_display = serializers.SerializerMethodField()
    fe2o3_display = serializers.SerializerMethodField()
    fe_display = serializers.SerializerMethodField()
    mgo_display = serializers.SerializerMethodField()
    sio2_display = serializers.SerializerMethodField()
    mc_display = serializers.SerializerMethodField()
    sm_display = serializers.SerializerMethodField()
    allocated_tonnage = serializers.SerializerMethodField()

    class Meta:
        model = SamplesPsiView
        fields = [
            "id",
            "iup_id", "iup_code",
            # "iup_name",
            "date_sample",
            "type_sample",
            # "sample_method",
            "material_psi",
            "stockpile",
            "dome_psi",
            "batch_code",
            "total_ore",
            "allocated_tonnage",
            "sample_id",
            "allocated_tonnage",
            "ni", "ni_display",
            "co", "co_display",
            "al2o3", "al2o3_display",
            "fe2o3", "fe2o3_display",
            "fe", "fe_display",
            "mgo", "mgo_display",
            "sio2", "sio2_display",
            "mc", "mc_display",
            "sm", "sm_display"
        ]

    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def allocated_tonnage(self, obj):
        return self._fmt_decimal(obj.ni)
    
    def get_ni_display(self, obj):
        return self._fmt_decimal(obj.ni)

    def get_co_display(self, obj):
        return self._fmt_decimal(obj.co)

    def get_al2o3_display(self, obj):
        return self._fmt_decimal(obj.al2o3)

    def get_fe2o3_display(self, obj):
        return self._fmt_decimal(obj.fe2o3)

    def get_fe_display(self, obj):
        return self._fmt_decimal(obj.fe)

    def get_mgo_display(self, obj):
        return self._fmt_decimal(obj.mgo)

    def get_sio2_display(self, obj):
        return self._fmt_decimal(obj.sio2)

    def get_mc_display(self, obj):
        return self._fmt_decimal(obj.mc)
    
    def get_sm_display(self, obj):
        return self._fmt_decimal(obj.sm)