from rest_framework import serializers
from master.models import SourceMinesLoading

class SourceMinesLoadingSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)
    source_label = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SourceMinesLoading
        fields = [
            "id",
            "iup", "iup_code", "iup_name",

            "loading_point",
            "category",
            "description",

            "source",        # FK ke SourceMines
            "source_label",  # readonly

            "status",
            "latitude",
            "longitude",
            "geometry",
            "extra_properties",
        ]

    def get_source_label(self, obj):
        if not obj.source:
            return None
        # sesuaikan field di SourceMines kamu
        return getattr(obj.source, "sources_area", None) or getattr(obj.source, "name", None) or str(obj.source)

    def validate_loading_point(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Loading point wajib diisi.")
        return v

    def validate(self, attrs):
        iup = attrs.get("iup") or (self.instance.iup if self.instance else None)
        loading_point = attrs.get("loading_point") or (self.instance.loading_point if self.instance else None)

        if iup and loading_point:
            qs = SourceMinesLoading.objects.filter(iup=iup, loading_point__iexact=loading_point.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"loading_point": "Loading point sudah ada untuk IUP ini."})

        return attrs