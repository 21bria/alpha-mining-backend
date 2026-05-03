from rest_framework import serializers
from geology.models.geology_sample_crm_certified import SampleCrmCertified


class CRMCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleCrmCertified
        fields = [
            "id",
            "oreas_name",
            "ni",
            "co",
            "al2o3",
            "cao",
            "cr2o3",
            "fe2o3",
            "fe",
            "k2o",
            "mgo",
            "mno",
            "na2o",
            "p2o5",
            "p",
            "sio2",
            "tio2",
            "s",
            "cu",
            "zn",
            "ci",
            "so3",
            "loi",
            "sm",
            "user",
        ]

    def validate_oreas_name(self, value):
        oreas_name = (value or "").strip()
        qs = SampleCrmCertified.objects.filter(oreas_name__iexact=oreas_name)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Nama OREAS CRM Certificate sudah ada.")

        return oreas_name
