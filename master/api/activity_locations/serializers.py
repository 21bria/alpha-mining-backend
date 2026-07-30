import re

from rest_framework import serializers

from mining.models import MiningActivityLocation


def clean_code_part(value: str) -> str:
    value = str(value or "").strip().upper()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[^A-Z0-9\-]", "", value)
    return value


def build_activity_location_code(
    iup_obj,
    name: str | None,
) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    iup_part = clean_code_part(iup_code)
    name_part = clean_code_part(name or "NONAME")

    return f"{iup_part}{name_part}"


class MiningActivityLocationSerializer(
    serializers.ModelSerializer
):
    iup_code = serializers.CharField(
        source="iup.iup_code",
        read_only=True,
    )
    iup_name = serializers.CharField(
        source="iup.iup_name",
        read_only=True,
    )

    user_id = serializers.IntegerField(
        source="user.id",
        read_only=True,
    )
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

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
        extra_kwargs = {
            # IUP boleh tidak dikirim oleh site user.
            # Nanti diisi lewat perform_create().
            "iup": {
                "required": False,
                "allow_null": True,
            },
        }

    def validate_name(self, value: str):
        name = (value or "").strip()

        if not name:
            raise serializers.ValidationError(
                "Name wajib diisi."
            )

        return name

    def validate(self, attrs):
        iup_obj = (
            attrs.get("iup")
            or (
                self.instance.iup
                if self.instance
                else None
            )
        )

        name = (
            attrs.get("name")
            or (
                self.instance.name
                if self.instance
                else None
            )
        )

        # Jangan wajibkan IUP di sini.
        # Untuk site user, IUP akan masuk melalui perform_create().
        if iup_obj and name:
            duplicate_qs = (
                MiningActivityLocation.objects
                .filter(
                    iup=iup_obj,
                    name__iexact=name.strip(),
                )
            )

            if self.instance:
                duplicate_qs = duplicate_qs.exclude(
                    pk=self.instance.pk
                )

            if duplicate_qs.exists():
                raise serializers.ValidationError({
                    "name": (
                        "Activity location sudah ada "
                        "untuk IUP ini."
                    ),
                })

            code = build_activity_location_code(
                iup_obj,
                name,
            )

            code_qs = (
                MiningActivityLocation.objects
                .filter(code=code)
            )

            if self.instance:
                code_qs = code_qs.exclude(
                    pk=self.instance.pk
                )

            if code_qs.exists():
                raise serializers.ValidationError({
                    "code": (
                        f"Code '{code}' sudah digunakan."
                    ),
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            validated_data["user"] = user

        iup_obj = validated_data.get("iup")
        name = validated_data.get("name")

        if not iup_obj:
            raise serializers.ValidationError({
                "iup": "IUP aktif user tidak ditemukan.",
            })

        validated_data["code"] = (
            build_activity_location_code(
                iup_obj,
                name,
            )
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        iup_obj = validated_data.get(
            "iup",
            instance.iup,
        )
        name = validated_data.get(
            "name",
            instance.name,
        )

        validated_data["code"] = (
            build_activity_location_code(
                iup_obj,
                name,
            )
        )

        return super().update(
            instance,
            validated_data,
        )