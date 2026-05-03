from rest_framework import serializers
from master.models import MineIUP

class MineIUPSerializer(serializers.ModelSerializer):
    class Meta:
        model = MineIUP
        fields = ["id", "iup_code", "iup_name", "geometry", "center_lat", "center_lng", "default_zoom"]

    def validate_iup_name(self, value: str):
        name = value.strip()
        qs = MineIUP.objects.filter(iup_name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nama IUP sudah ada.")
        return name
        
    def validate_iup_code(self, value: str):
        code = value.strip()
        qs = MineIUP.objects.filter(iup_code__iexact=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Kode IUP sudah ada.")
        return code