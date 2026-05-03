from rest_framework import serializers
from geology.models import AssayRoa
from django.utils import timezone

class AssayRoaSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    release_roa_display = serializers.SerializerMethodField()
    ni_display = serializers.SerializerMethodField()
    co_display = serializers.SerializerMethodField()
    al2o3_display = serializers.SerializerMethodField()
    fe2o3_display = serializers.SerializerMethodField()
    fe_display = serializers.SerializerMethodField()
    mgo_display = serializers.SerializerMethodField()
    sio2_display = serializers.SerializerMethodField()
    mc_display = serializers.SerializerMethodField()
    class Meta:
        model = AssayRoa
        fields = [
            "id",
            "iup", "iup_code", "iup_name",

            # "release_roa","release_date","release_time","job_number",

            # "sample_id",
            # "ni","co","al2o3","cao","cr2o3","fe2o3","fe","k2o","mgo","mno","na2o","p2o5",
            # "p","sio2","tio2","s","cu","zn","ci","so3","loi","total","wt_wet","wt_dry","mc","p75um",
            # "_5mm","problem",
            "release_roa",
            "release_roa_display",
            "job_number",
            "sample_id",
            "ni", "ni_display",
            "co", "co_display",
            "al2o3", "al2o3_display",
            "fe2o3", "fe2o3_display",
            "fe", "fe_display",
            "mgo", "mgo_display",
            "sio2", "sio2_display",
            "mc", "mc_display",
        ]
    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_release_roa_display(self, obj):
        if not obj.release_roa:
            return "-"
        dt = timezone.localtime(obj.release_roa)
        return dt.strftime("%d-%m-%Y %H:%M")

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