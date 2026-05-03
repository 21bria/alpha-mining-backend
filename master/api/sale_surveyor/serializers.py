from rest_framework import serializers
from master.models import SellingSurveyor

class SellingSurveyorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SellingSurveyor
        fields = ["id","code_surveyor","name_surveyor","description","user"]
        read_only_fields = ["user"]

    def validate_code_surveyor(self, value: str):
        code_surveyor = value.strip()
        qs = SellingSurveyor.objects.filter(code_surveyor__iexact=code_surveyor)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Code sudah ada.")
        return code_surveyor
    
    def validate_name_surveyor(self, value: str):
        name_surveyor = value.strip()
        qs = SellingSurveyor.objects.filter(name_surveyor__iexact=name_surveyor)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nama sudah ada.")
        return name_surveyor
    
    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)