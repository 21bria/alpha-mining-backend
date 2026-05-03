from rest_framework import serializers
from master.models import SourceMinesDumping
from core.permissions import user_allowed_iup_ids

class SourceMinesDumpingSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    ALLOWED_CATEGORIES = {"Stockpile", "General"}

    class Meta:
        model = SourceMinesDumping
        fields = [
            "id",
            "iup", "iup_code", "iup_name",
            "dumping_point",
            "description",
            "category",
            "compositing",
            "status",
            "latitude",
            "longitude",
            "geometry",
            "extra_properties",
            "user",
        ]
        read_only_fields = ["user"]

    def validate_dumping_point(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Dumping point wajib diisi.")
        return v

    def validate_category(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Category wajib diisi.")
        if v not in self.ALLOWED_CATEGORIES:
            raise serializers.ValidationError("Category harus 'Stockpile' atau 'General'.")
        return v

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        if request and u and u.is_authenticated:
            # SITE_USER: paksa iup dari default / active iup
            if u.is_site_user and request.method in ("POST", "PUT", "PATCH"):
                iup_id = getattr(u, "default_iup_id", None) or getattr(u, "active_iup_id", None) or getattr(u, "iup_id", None)
                if not iup_id:
                    allowed = user_allowed_iup_ids(u) or set()
                    iup_id = next(iter(allowed), None)

                if not iup_id:
                    raise serializers.ValidationError({"iup": "User belum punya default/active IUP."})

                attrs["iup_id"] = int(iup_id)

            # MANAGEMENT: kalau pilih iup, harus allowed
            if getattr(u, "is_management", False) and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(u)
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({"iup": "IUP tidak termasuk allowed untuk user ini."})

        # ambil iup_id final
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
        else:
            iup = attrs.get("iup") or (self.instance.iup if self.instance else None)
            iup_id = getattr(iup, "id", None)

        dumping_point = attrs.get("dumping_point") or (self.instance.dumping_point if self.instance else None)

        if iup_id and dumping_point:
            qs = SourceMinesDumping.objects.filter(
                iup_id=iup_id,
                dumping_point__iexact=dumping_point.strip(),
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "dumping_point": "Dumping point sudah ada untuk IUP ini."
                })

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user
        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)
        return super().update(instance, validated_data)