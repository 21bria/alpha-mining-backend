from rest_framework import serializers
from master.models import SourceMines
from rest_framework import serializers

class SourceMinesSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    class Meta:
        model = SourceMines
        fields = [
            "id",
            "iup",        # FK untuk create/edit
            "iup_code",   # readonly
            "iup_name",   # readonly

            "sources_area",
            "description",
            "latitude",
            "longitude",
            "geometry",
            "extra_properties",
            "user",
        ]
        read_only_fields = ["user"]

    def validate_sources_area(self, value: str):
        v = value.strip()
        if not v:
            raise serializers.ValidationError("Source area wajib diisi.")
        return v

    def validate(self, attrs):
        # validasi unik: (iup, sources_area)
        iup = attrs.get("iup") or (self.instance.iup if self.instance else None)
        sources_area = attrs.get("sources_area") or (self.instance.sources_area if self.instance else None)

        if iup and sources_area:
            qs = SourceMines.objects.filter(iup=iup, sources_area__iexact=sources_area.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"sources_area": "sources_area sudah ada untuk IUP ini."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)