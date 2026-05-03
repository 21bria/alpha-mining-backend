from rest_framework import serializers
from master.models import OreTruckFactor, MineIUP, Material
from core.permissions import user_allowed_iup_ids
import re


def clean_code_part(value: str) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    return s


def build_ore_truck_factor_code(iup_obj, material_obj, type_tf: str | None) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    material_id = getattr(material_obj, "id", None) or "NOMAT"
    type_part = clean_code_part(type_tf or "NOTYPE")

    iup_part = clean_code_part(iup_code)
    material_part = clean_code_part(material_id)

    return f"{iup_part}-{material_part}-{type_part}"


class OreTruckFactorSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    material_name = serializers.CharField(source="material.name", read_only=True)
    material_code = serializers.CharField(source="material.code", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = OreTruckFactor
        fields = [
            "id",
            "code",

            "iup",
            "iup_code",
            "iup_name",

            "type_tf",

            "material",
            "material_code",
            "material_name",

            "density",
            "bcm",
            "ton",
            "status",

            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "code",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate_type_tf(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Type truck factor wajib diisi.")
        return v.upper()

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        if request and u and u.is_authenticated:
            if getattr(u, "is_site_user", False) and request.method in ("POST", "PUT", "PATCH"):
                if not getattr(u, "default_iup_id", None):
                    raise serializers.ValidationError({"iup": "User belum punya default IUP."})
                attrs["iup_id"] = int(u.default_iup_id)

            if getattr(u, "is_management", False) and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(u)
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({"iup": "IUP tidak termasuk allowed untuk user ini."})

        # final iup
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
            iup_obj = attrs.get("iup") or MineIUP.objects.filter(pk=iup_id).first()
        else:
            iup_obj = attrs.get("iup") or (self.instance.iup if self.instance else None)
            iup_id = getattr(iup_obj, "id", None)

        # final material
        if "material_id" in attrs:
            material_id = attrs["material_id"]
            material_obj = attrs.get("material") or Material.objects.filter(pk=material_id).first()
        else:
            material_obj = attrs.get("material") or (self.instance.material if self.instance else None)
            material_id = getattr(material_obj, "id", None)

        # final type_tf
        type_tf = attrs.get("type_tf")
        if type_tf is None and self.instance:
            type_tf = self.instance.type_tf

        if type_tf:
            type_tf = type_tf.strip().upper()

        if not iup_obj:
            raise serializers.ValidationError({"iup": "IUP wajib diisi."})

        if not material_obj:
            raise serializers.ValidationError({"material": "Material wajib diisi."})

        if not type_tf:
            raise serializers.ValidationError({"type_tf": "Type truck factor wajib diisi."})

        # unik: iup + type_tf + material
        qs = OreTruckFactor.objects.filter(
            iup_id=iup_id,
            material_id=material_id,
            type_tf__iexact=type_tf,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "type_tf": "Truck factor sudah ada untuk kombinasi IUP, material, dan type ini."
            })

        # cek code unik
        code = build_ore_truck_factor_code(iup_obj, material_obj, type_tf)
        qs_code = OreTruckFactor.objects.filter(code=code)
        if self.instance:
            qs_code = qs_code.exclude(pk=self.instance.pk)

        if qs_code.exists():
            raise serializers.ValidationError({
                "non_field_errors": [f"Code '{code}' sudah digunakan."]
            })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        type_tf = (validated_data.get("type_tf") or "").strip().upper()
        validated_data["type_tf"] = type_tf

        iup_obj = validated_data.get("iup")
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(pk=validated_data["iup_id"]).first()

        material_obj = validated_data.get("material")
        if not material_obj and validated_data.get("material_id"):
            material_obj = Material.objects.filter(pk=validated_data["material_id"]).first()

        validated_data["code"] = build_ore_truck_factor_code(iup_obj, material_obj, type_tf)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user

        if getattr(u, "is_site_user", False):
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)

        type_tf = validated_data.get("type_tf", instance.type_tf)
        type_tf = (type_tf or "").strip().upper()
        validated_data["type_tf"] = type_tf

        iup_obj = validated_data.get("iup", instance.iup)
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(pk=validated_data["iup_id"]).first()

        material_obj = validated_data.get("material", instance.material)
        if not material_obj and validated_data.get("material_id"):
            material_obj = Material.objects.filter(pk=validated_data["material_id"]).first()

        validated_data["code"] = build_ore_truck_factor_code(iup_obj, material_obj, type_tf)

        return super().update(instance, validated_data)