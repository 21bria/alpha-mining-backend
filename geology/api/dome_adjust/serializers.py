from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from rest_framework import serializers

from geology.models import DomeAdjustment
from core.permissions import user_allowed_iup_ids
from geology.services.dome_adjustment import get_tonnage_by_dome, scale_dome_tonnage


class DomeAdjustmentSerializer(serializers.ModelSerializer):
    dome_name = serializers.CharField(source="dome.name", read_only=True)
    dome_code = serializers.CharField(source="dome.code", read_only=True)

    iup_id = serializers.IntegerField(source="dome.iup.id", read_only=True)
    iup_code = serializers.CharField(source="dome.iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="dome.iup.iup_name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = DomeAdjustment
        fields = [
            "id",
            "dome",
            "dome_code",
            "dome_name",
            "iup_id",
            "iup_code",
            "iup_name",
            "current_total",
            "target_total",
            "scale_factor",
            "description",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "current_total",
            "scale_factor",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate_target_total(self, value):
        if value is None:
            raise serializers.ValidationError("Target total wajib diisi.")
        value = Decimal(str(value))
        if value <= Decimal("0"):
            raise serializers.ValidationError("Target tonnage harus lebih dari 0.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        dome_obj = attrs.get("dome") or getattr(self.instance, "dome", None)
        target_total = attrs.get("target_total", getattr(self.instance, "target_total", None))
        description = attrs.get("description", getattr(self.instance, "description", None))

        if not dome_obj:
            raise serializers.ValidationError({"dome": "Dome wajib diisi."})

        if target_total is None:
            raise serializers.ValidationError({"target_total": "Target total wajib diisi."})

        target_total = Decimal(str(target_total))
        if target_total <= Decimal("0"):
            raise serializers.ValidationError({"target_total": "Target tonnage harus lebih dari 0."})

        if not description:
            raise serializers.ValidationError({"description": "Description wajib diisi."})

        if request and u and u.is_authenticated:
            allowed = user_allowed_iup_ids(u)
            dome_iup_id = getattr(dome_obj, "iup_id", None)

            if not (getattr(u, "is_system", False) or getattr(u, "is_superuser", False)):
                if allowed and dome_iup_id and int(dome_iup_id) not in allowed:
                    raise serializers.ValidationError({
                        "dome": "Dome tidak termasuk IUP yang diizinkan untuk user ini."
                    })

        qs = DomeAdjustment.objects.filter(
            dome=dome_obj,
            target_total=target_total,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Penyesuaian untuk dome ini dengan target {target_total} sudah pernah dilakukan."
                ]
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        dome_obj = validated_data["dome"]
        target_total = Decimal(str(validated_data["target_total"]))

        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        # ambil total sebelum diubah
        current_total_before = get_tonnage_by_dome(dome_obj.id)
        if current_total_before <= Decimal("0"):
            raise serializers.ValidationError({
                "non_field_errors": ["Current total dome = 0. Adjustment tidak bisa dilakukan."]
            })

        # update semua production
        current_total, scale_factor = scale_dome_tonnage(
            dome_id=dome_obj.id,
            target_total=target_total,
        )

        validated_data["current_total"] = current_total
        validated_data["scale_factor"] = scale_factor

        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        dome_obj = validated_data.get("dome", instance.dome)
        target_total = Decimal(str(validated_data.get("target_total", instance.target_total)))

        current_total_before = get_tonnage_by_dome(dome_obj.id)
        if current_total_before <= Decimal("0"):
            raise serializers.ValidationError({
                "non_field_errors": ["Current total dome = 0. Adjustment tidak bisa dilakukan."]
            })

        # update semua production lagi sesuai target baru
        current_total, scale_factor = scale_dome_tonnage(
            dome_id=dome_obj.id,
            target_total=target_total,
        )

        validated_data["current_total"] = current_total
        validated_data["scale_factor"] = scale_factor

        return super().update(instance, validated_data)