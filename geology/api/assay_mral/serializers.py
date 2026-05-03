from rest_framework import serializers
from django.utils import timezone
from geology.models import AssayMral

class AssayMralSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    release_mral_display = serializers.SerializerMethodField()
    ni_display = serializers.SerializerMethodField()
    co_display = serializers.SerializerMethodField()
    fe2o3_display = serializers.SerializerMethodField()
    fe_display = serializers.SerializerMethodField()
    mgo_display = serializers.SerializerMethodField()
    sio2_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AssayMral
        fields = [
            "id",
            "iup", "iup_code", "iup_name",

            "release_mral",
            "release_mral_display",
            "job_number",

            "sample_id",
            "ni",
            "ni_display",
            "co",
            "co_display",
            "fe",
            "fe_display",
            "fe2o3",
            "fe2o3_display",
            "mgo",
            "mgo_display",
            "sio2",
            "sio2_display"
        ]

    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_release_mral_display(self, obj):
        if not obj.release_mral:
            return "-"
        dt = timezone.localtime(obj.release_mral)
        return dt.strftime("%d-%m-%Y %H:%M")

    def get_ni_display(self, obj):
        return self._fmt_decimal(obj.ni)

    def get_co_display(self, obj):
        return self._fmt_decimal(obj.co)


    def get_fe2o3_display(self, obj):
        return self._fmt_decimal(obj.fe2o3)

    def get_fe_display(self, obj):
        return self._fmt_decimal(obj.fe)

    def get_mgo_display(self, obj):
        return self._fmt_decimal(obj.mgo)

    def get_sio2_display(self, obj):
        return self._fmt_decimal(obj.sio2)

 