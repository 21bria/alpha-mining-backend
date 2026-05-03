from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from geology.models import DomeMerge
from core.permissions import user_allowed_iup_ids
from geology.services.dome_merge import (
    get_tonnage_by_dome,
    merge_dome_productions,
    build_merge_ref,
)


class DomeMergeSerializer(serializers.ModelSerializer):
    original_dome_code = serializers.CharField(source="original_dome.code", read_only=True)
    original_dome_name = serializers.CharField(source="original_dome.name", read_only=True)

    dome_second_code = serializers.CharField(source="dome_second.code", read_only=True)
    dome_second_name = serializers.CharField(source="dome_second.name", read_only=True)

    iup_id = serializers.IntegerField(source="iup.id", read_only=True)
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    undone_by_id = serializers.IntegerField(source="undone_by.id", read_only=True)
    undone_by_username = serializers.CharField(source="undone_by.username", read_only=True)

    class Meta:
        model = DomeMerge
        fields = [
            "id",
            "iup",
            "iup_id",
            "iup_code",
            "iup_name",
            "original_dome",
            "original_dome_code",
            "original_dome_name",
            "tonnage_primary",
            "dome_second",
            "dome_second_code",
            "dome_second_name",
            "tonnage_second",
            "ref_id",
            "status",
            "is_undone",
            "undone_at",
            "undone_by",
            "undone_by_id",
            "undone_by_username",
            "undo_notes",
            "description",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "iup",
            "tonnage_primary",
            "tonnage_second",
            "ref_id",
            "status",
            "is_undone",
            "undone_at",
            "undone_by",
            "undone_by_id",
            "undone_by_username",
            "undo_notes",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        original_dome = attrs.get("original_dome") or getattr(self.instance, "original_dome", None)
        dome_second = attrs.get("dome_second") or getattr(self.instance, "dome_second", None)
        description = attrs.get("description", getattr(self.instance, "description", None))

        if not original_dome:
            raise serializers.ValidationError({"original_dome": "Original dome wajib diisi."})

        if not dome_second:
            raise serializers.ValidationError({"dome_second": "Target dome wajib diisi."})

        if original_dome.id == dome_second.id:
            raise serializers.ValidationError({
                "non_field_errors": ["Original dome dan target dome tidak boleh sama."]
            })

        if getattr(original_dome, "iup_id", None) != getattr(dome_second, "iup_id", None):
            raise serializers.ValidationError({
                "non_field_errors": ["Compositing hanya boleh untuk dome dalam IUP yang sama."]
            })

        if not description:
            raise serializers.ValidationError({"description": "Description wajib diisi."})

        if request and u and u.is_authenticated:
            allowed = user_allowed_iup_ids(u)
            original_iup_id = getattr(original_dome, "iup_id", None)
            target_iup_id = getattr(dome_second, "iup_id", None)

            if not (getattr(u, "is_system", False) or getattr(u, "is_superuser", False)):
                if allowed:
                    if original_iup_id and int(original_iup_id) not in allowed:
                        raise serializers.ValidationError({
                            "original_dome": "Original dome tidak termasuk IUP yang diizinkan."
                        })
                    if target_iup_id and int(target_iup_id) not in allowed:
                        raise serializers.ValidationError({
                            "dome_second": "Target dome tidak termasuk IUP yang diizinkan."
                        })

        # validasi tonnage di serializer juga, supaya cepat gagal sebelum service
        original_total = get_tonnage_by_dome(original_dome.id)
        if original_total <= Decimal("0"):
            raise serializers.ValidationError({
                "original_dome": "Original dome belum punya produksi."
            })

        target_total = get_tonnage_by_dome(dome_second.id)
        if target_total <= Decimal("0"):
            raise serializers.ValidationError({
                "dome_second": "Target dome belum punya produksi, tidak bisa compositing."
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        original_dome = validated_data["original_dome"]
        dome_second = validated_data["dome_second"]

        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        validated_data["iup"] = original_dome.iup
        validated_data["ref_id"] = build_merge_ref(original_dome.id, dome_second.id)
        validated_data["status"] = "MERGED"
        validated_data["is_undone"] = False

        merge_result = merge_dome_productions(
            original_dome_id=original_dome.id,
            target_dome_id=dome_second.id,
            ref_id=validated_data["ref_id"],
        )

        validated_data["tonnage_primary"] = merge_result["original_total"]
        validated_data["tonnage_second"] = merge_result["target_total"]

        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        raise serializers.ValidationError({
            "non_field_errors": ["Data compositing tidak boleh diubah. Gunakan undo jika ingin membatalkan."]
        })