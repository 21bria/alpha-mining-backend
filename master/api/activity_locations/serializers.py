import re
from rest_framework import serializers

from mining.models import MiningActivityLocation

def clean_code_part(value: str) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    return s


def build_activity_location_code(iup_obj, name: str | None) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    iup_part = clean_code_part(iup_code)
    name_part = clean_code_part(name or "NONAME")
    return f"{iup_part}{name_part}"


class MiningActivityLocationSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = MiningActivityLocation
        fields = [
            "id",
            "code",
            "iup",
            "iup_code",
            "iup_name",
            "name",
            "description",
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
            "iup_code",
            "iup_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        iup_obj = attrs.get("iup") or getattr(self.instance, "iup", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)

        if not iup_obj:
            raise serializers.ValidationError({"iup": "IUP is required."})

        if not name:
            raise serializers.ValidationError({"name": "Name is required."})

        qs = MiningActivityLocation.objects.filter(
            iup=iup_obj,
            name__iexact=name.strip(),
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Data Activity Location sudah ada untuk IUP '{iup_obj.iup_code}' dan name '{name}'."
                ]
            })

        code = build_activity_location_code(iup_obj, name)

        qs_code = MiningActivityLocation.objects.filter(code=code)
        if self.instance:
            qs_code = qs_code.exclude(pk=self.instance.pk)

        if qs_code.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Code '{code}' sudah digunakan."
                ]
            })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        iup_obj = validated_data.get("iup")
        name = validated_data.get("name")
        validated_data["code"] = build_activity_location_code(iup_obj, name)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        iup_obj = validated_data.get("iup", instance.iup)
        name = validated_data.get("name", instance.name)
        validated_data["code"] = build_activity_location_code(iup_obj, name)

        return super().update(instance, validated_data)