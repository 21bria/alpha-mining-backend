from rest_framework import serializers
from master.models import OreClass, MineIUP, Material
from core.permissions import user_allowed_iup_ids
import re


def clean_code_part(value: str) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    return s


def build_ore_class_code(iup_obj, material_obj, ore_class: str | None) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    material_id = getattr(material_obj, "id", None) or "NOMAT"
    ore_class_part = clean_code_part(ore_class or "NOCLASS")

    iup_part = clean_code_part(iup_code)
    material_part = clean_code_part(material_id)

    return f"{iup_part}-{material_part}-{ore_class_part}"


class OreClassSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    material_name = serializers.CharField(source="material.name", read_only=True)
    material_code = serializers.CharField(source="material.code", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = OreClass
        fields = [
            "id",
            "code",

            "iup",
            "iup_code",
            "iup_name",

            "material",
            "material_code",
            "material_name",

            "ore_class",

            "ni_min",
            "ni_max",

            "mgo_min",
            "mgo_max",

            "fe_min",
            "fe_max",

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

    def validate_ore_class(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Ore class wajib diisi.")
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

        # iup final
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
            iup_obj = attrs.get("iup") or MineIUP.objects.filter(pk=iup_id).first()
        else:
            iup_obj = attrs.get("iup") or (self.instance.iup if self.instance else None)
            iup_id = getattr(iup_obj, "id", None)

        # material final
        if "material_id" in attrs:
            material_id = attrs["material_id"]
            material_obj = attrs.get("material") or Material.objects.filter(pk=material_id).first()
        else:
            material_obj = attrs.get("material") or (self.instance.material if self.instance else None)
            material_id = getattr(material_obj, "id", None)

        # ore_class final
        ore_class = attrs.get("ore_class")
        if ore_class is None and self.instance:
            ore_class = self.instance.ore_class

        if ore_class:
            ore_class = ore_class.strip().upper()

        if not iup_obj:
            raise serializers.ValidationError({"iup": "IUP wajib diisi."})

        if not material_obj:
            raise serializers.ValidationError({"material": "Material wajib diisi."})

        if not ore_class:
            raise serializers.ValidationError({"ore_class": "Ore class wajib diisi."})

        # unik: iup + material + ore_class
        qs = OreClass.objects.filter(
            iup_id=iup_id,
            material_id=material_id,
            ore_class__iexact=ore_class,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "ore_class": "Ore class sudah ada untuk kombinasi IUP dan material ini."
            })

        # cek code unik juga
        code = build_ore_class_code(iup_obj, material_obj, ore_class)
        qs_code = OreClass.objects.filter(code=code)
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

        ore_class = (validated_data.get("ore_class") or "").strip().upper()
        validated_data["ore_class"] = ore_class

        iup_obj = validated_data.get("iup")
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(pk=validated_data["iup_id"]).first()

        material_obj = validated_data.get("material")
        if not material_obj and validated_data.get("material_id"):
            material_obj = Material.objects.filter(pk=validated_data["material_id"]).first()

        validated_data["code"] = build_ore_class_code(iup_obj, material_obj, ore_class)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user

        if getattr(u, "is_site_user", False):
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)

        ore_class = validated_data.get("ore_class", instance.ore_class)
        ore_class = (ore_class or "").strip().upper()
        validated_data["ore_class"] = ore_class

        iup_obj = validated_data.get("iup", instance.iup)
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(pk=validated_data["iup_id"]).first()

        material_obj = validated_data.get("material", instance.material)
        if not material_obj and validated_data.get("material_id"):
            material_obj = Material.objects.filter(pk=validated_data["material_id"]).first()

        validated_data["code"] = build_ore_class_code(iup_obj, material_obj, ore_class)

        return super().update(instance, validated_data)