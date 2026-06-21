from rest_framework import serializers
from master.models import SourcePitDome


class SourcePitDomeSerializer(serializers.ModelSerializer):
    iup = serializers.IntegerField(source="loading_point.iup_id", read_only=True)
    iup_code = serializers.CharField(source="loading_point.iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="loading_point.iup.iup_name", read_only=True)

    loading_point_label = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SourcePitDome
        fields = [
            "id",
            "iup",
            "iup_code",
            "iup_name",
            "loading_point",
            "loading_point_label",
            "dome",
            "dome_type",
            "description",
            "compositing",
            "status_dome",
            "is_active",
            "direct_sale",
            "latitude",
            "longitude",
            "geometry",
            "extra_properties",
            "user",
        ]

        read_only_fields = [
            "user",
            "iup",
            "iup_code",
            "iup_name",
            "loading_point_label",
        ]

    def get_loading_point_label(self, obj):
        if not obj.loading_point:
            return None

        return (
            getattr(obj.loading_point, "loading_point", None)
            or getattr(obj.loading_point, "source_loading", None)
            or getattr(obj.loading_point, "name", None)
            or getattr(obj.loading_point, "code", None)
            or str(obj.loading_point_id)
        )
    
    def validate_dome(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Dome wajib diisi.")
        return v

    def validate(self, attrs):
        loading_point = attrs.get("loading_point") or (
            self.instance.loading_point if self.instance else None
        )
        dome = attrs.get("dome") or (
            self.instance.dome if self.instance else None
        )

        if loading_point and dome:
            qs = SourcePitDome.objects.filter(
                loading_point=loading_point,
                dome__iexact=dome.strip(),
            )

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "dome": "Dome sudah ada untuk loading point ini."
                })

        return attrs