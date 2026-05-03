from rest_framework import serializers
from datetime import datetime, timedelta
from mining.models import Rainfall,RainfallPoint
from master.models import MineIUP
from core.permissions import user_allowed_iup_ids

class RainfallSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    point_id = serializers.PrimaryKeyRelatedField(
        source="point",
        queryset=RainfallPoint.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    point_name = serializers.CharField(source="point.name", read_only=True)

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = Rainfall
        fields = [
            "id",
            "code",
            "iup", "iup_code", "iup_name",
            "date",
            "point",      
            "point_id",   
            "point_name",
            "milimeter",
            "description",
            "user",
        ]
        read_only_fields = ["user", "code", "point"]

    def _build_code(self, iup_obj, date_value, point_obj):
        iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
        d = date_value.strftime("%Y%m%d") if date_value else "NODATE"

        point_name = getattr(point_obj, "name", "") or "NOPOINT"
        point_val = point_name.strip().upper().replace(" ", "")

        return f"RF-{iup_code}-{d}-{point_val}"

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        iup_obj = attrs.get("iup") or getattr(self.instance, "iup", None)
        date_value = attrs.get("date") or getattr(self.instance, "date", None)
        point_obj = attrs.get("point") or getattr(self.instance, "point", None)

        if request and u and u.is_authenticated:
            if u.is_site_user and request.method in ("POST", "PUT", "PATCH"):
                if not u.default_iup_id:
                    raise serializers.ValidationError({"iup": "User belum punya default IUP."})
                attrs["iup_id"] = int(u.default_iup_id)

            if u.is_management and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(u)
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({
                        "iup": "IUP tidak termasuk allowed untuk user ini."
                    })

        iup_id = None
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
        elif iup_obj is not None:
            iup_id = getattr(iup_obj, "id", None)

        if iup_id and date_value and point_obj:
            qs = Rainfall.objects.filter(
                iup_id=iup_id,
                date=date_value,
                point=point_obj,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "non_field_errors": [
                        "Data rainfall dengan kombinasi IUP, date, dan point sudah ada."
                    ]
                })

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user

        iup_obj = validated_data.get("iup")
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(id=validated_data["iup_id"]).first()

        point_obj = validated_data.get("point")

        validated_data["code"] = self._build_code(
            iup_obj=iup_obj,
            date_value=validated_data.get("date"),
            point_obj=point_obj,
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user

        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)

        iup_obj = validated_data.get("iup", instance.iup)
        point_obj = validated_data.get("point", instance.point)

        validated_data["code"] = self._build_code(
            iup_obj=iup_obj,
            date_value=validated_data.get("date", instance.date),
            point_obj=point_obj,
        )

        return super().update(instance, validated_data)
    
class RainfallPointSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    class Meta:
        model = RainfallPoint
        fields = ["id","iup","iup_code","iup_name","name","description","user"]
        read_only_fields = ["user"]

    def _build_code(self, iup_obj, name):
        iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
        name_val = (name or "").strip().upper().replace(" ", "")
        return f"RFP-{iup_code}-{name_val}"

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        # ambil nilai final (buat create/update)
        iup_obj = attrs.get("iup") or getattr(self.instance, "iup", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)

        if request and u and u.is_authenticated:
            if u.is_site_user and request.method in ("POST", "PUT", "PATCH"):
                if not u.default_iup_id:
                    raise serializers.ValidationError({"iup": "User belum punya default IUP."})
                attrs["iup_id"] = int(u.default_iup_id)
                if not iup_obj:
                    iup_obj = getattr(self.instance, "iup", None)
                    if not iup_obj and hasattr(Rainfall, "iup"):
                        # nanti create() akan pakai iup_id, untuk validasi duplikat cukup pakai iup_id bila perlu
                        pass

            if u.is_management and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(u)
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({"iup": "IUP tidak termasuk allowed untuk user ini."})


        # validasi duplikasi kombinasi utama
        iup_id = None
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
        elif iup_obj is not None:
            iup_id = getattr(iup_obj, "id", None)

        if iup_id and name:
            qs = RainfallPoint.objects.filter(
                iup_id=iup_id,
                name=name
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "non_field_errors": [
                        "Data Points dengan kombinasi IUP dan name sudah ada."
                    ]
                })

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user

        iup_obj = validated_data.get("iup")
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(id=validated_data["iup_id"]).first()

        validated_data["code"] = self._build_code(
            iup_obj=iup_obj,
            name=validated_data.get("name"),
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user

        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)

        iup_obj = validated_data.get("iup", instance.iup)

        validated_data["code"] = self._build_code(
            iup_obj=iup_obj,
            name=validated_data.get("name", instance.name)
        )

        return super().update(instance, validated_data)