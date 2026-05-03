from rest_framework import serializers
import re

from mining.models import mineAdditionFactor


def clean_code_part(value: str) -> str:
    s = str(value or "").strip()
    s = re.sub(r"\s+", "", s)              # hapus semua spasi
    s = re.sub(r"[^A-Za-z0-9\-]", "", s)   # sisakan huruf, angka, strip
    return s


class FillFactorSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = mineAdditionFactor
        fields = [
            "id",
            "code",
            "iup", "iup_code", "iup_name",
            "type_unit",
            "material",
            "density_bcm",
            "density_lcm",
            "bucket_capacity",
            "validation",
            "description",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "code",
            "iup_code",
            "iup_name",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        iup_obj = attrs.get("iup") or getattr(self.instance, "iup", None)
        type_unit = attrs.get("type_unit") or getattr(self.instance, "type_unit", None)
        material = attrs.get("material") or getattr(self.instance, "material", None)

        if not iup_obj:
            raise serializers.ValidationError({"iup": "IUP is required."})

        if not type_unit:
            raise serializers.ValidationError({"type_unit": "Type unit is required."})

        if not material:
            raise serializers.ValidationError({"material": "Material is required."})

        qs = mineAdditionFactor.objects.filter(
            iup=iup_obj,
            type_unit__iexact=type_unit.strip(),
            material__iexact=material.strip(),
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Data fill factor sudah ada untuk IUP '{iup_obj.iup_code}', "
                    f"type_unit '{type_unit}', dan material '{material}'."
                ]
            })

        return attrs

    def _build_code(self, iup_obj, type_unit, material):
        iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
        iup_part = clean_code_part(iup_code)
        unit_part = clean_code_part(type_unit)
        material_part = clean_code_part(material)

        return f"{iup_part}{unit_part}{material_part}"

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        iup_obj = validated_data.get("iup")
        type_unit = validated_data.get("type_unit")
        material = validated_data.get("material")

        validated_data["code"] = self._build_code(iup_obj, type_unit, material)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        iup_obj = validated_data.get("iup", instance.iup)
        type_unit = validated_data.get("type_unit", instance.type_unit)
        material = validated_data.get("material", instance.material)

        validated_data["code"] = self._build_code(iup_obj, type_unit, material)

        return super().update(instance, validated_data)