from rest_framework import serializers
from master.models import Material

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ["id", "name", "categories","description"]

    def validate_name(self, value: str):
        name = value.strip()
        qs = Material.objects.filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Nama Material sudah ada.")
        return name
