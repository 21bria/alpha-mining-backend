from rest_framework import serializers
from master.models import BargeUnits

class BargeUnitsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BargeUnits
        fields = ["id","barge_code","barge_name","capacity","description","active","user"]
        read_only_fields = ["user"]

    def validate_barge_code(self, value: str):
        barge_code = value.strip()
        qs = BargeUnits.objects.filter(barge_code__iexact=barge_code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Code sudah ada.")
        return barge_code
    
    def validate_barge_name(self, value: str):
        barge_name = value.strip()
        qs = BargeUnits.objects.filter(barge_name__iexact=barge_name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nama sudah ada.")
        return barge_name
    
    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)