from rest_framework import serializers
from master.models import SourceMinesDome

class SourceMinesDomeSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    dumping_label = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SourceMinesDome
        fields = [
            "id",
            "iup",
            "iup_code",
            "iup_name",
            
            "pile_id",
            "description",
            "category",
            "compositing",

            "dumping",          # FK
            "dumping_label",    # readonly

            "dome_finish",
            "status_dome",

            "plan_ni_min",
            "plan_ni_max",

            "status",
            "direct_sale",

            "latitude",
            "longitude",
            "geometry",
            "extra_properties",

            "user",
        ]

        read_only_fields = ["user"]

    def get_dumping_label(self, obj):
        if not obj.dumping:
            return None
        return obj.dumping.dumping_point
    
    def validate_pile_id(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Dome point wajib diisi.")
        return v

    def validate(self, attrs):
        iup = attrs.get("iup") or (self.instance.iup if self.instance else None)
        pile_id = attrs.get("pile_id") or (self.instance.pile_id if self.instance else None)

        if iup and pile_id:
            qs = SourceMinesDome.objects.filter(iup=iup, pile_id__iexact=pile_id.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"pile_id": "Loading point sudah ada untuk IUP ini."})

        return attrs