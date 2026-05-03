from os import name
from rest_framework import serializers
from master.models import SellingCode
from core.permissions import user_allowed_iup_ids

class SellingCodeSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    ALLOWED_TYPES = {"LIS", "SAS"}

    class Meta:
        model = SellingCode
        fields = [
            "id",
            "iup", "iup_code", "iup_name",

            "code",
            "description",
            "type",
            "active",

            "truck_factors",
            "sublot_close",
            "group_close",
            "ritase_max",
            "tonnage", "ni", "fe","al2o3","co","mgo","sio2","cao","mno","cr2o3","sm","mc",
            "user",
        ]
        read_only_fields = ["user"]

    def validate_code(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Code wajib diisi.")
        return v

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        if request and u and u.is_authenticated:
            # SITE_USER: iup dipaksa dari default_iup_id
            if u.is_site_user and request.method in ("POST", "PUT", "PATCH"):
                if not u.default_iup_id:
                    raise serializers.ValidationError({"iup": "User belum punya default IUP."})
                attrs["iup_id"] = int(u.default_iup_id)

            # MANAGEMENT: kalau pilih iup, harus termasuk allowed
            if u.is_management and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(u)
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({"iup": "IUP tidak termasuk allowed untuk user ini."})

        # unik (iup, code)
        iup_id = None
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
        else:
            iup = attrs.get("iup") or (self.instance.iup if self.instance else None)
            iup_id = getattr(iup, "id", None)

        code = attrs.get("code") or (self.instance.code if self.instance else None)
        if iup_id and code:
            qs = SellingCode.objects.filter(iup_id=iup_id, code__iexact=code.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"code": "Code sudah ada untuk IUP ini."})

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user
        # SITE_USER: jangan boleh ganti iup
        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)
        return super().update(instance, validated_data)