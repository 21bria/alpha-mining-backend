from django.db import transaction
from rest_framework import serializers
from geology.models import domeStatusFinish,OreProductions
from master.models import SourceMinesDome
from selling.models import SellingBarging
from core.permissions import user_allowed_iup_ids


def build_dome_duplicate_key(dome_obj, status_dome: str | None) -> str:
    dome_id = getattr(dome_obj, "id", None) or "NODOME"
    status_part = (status_dome or "").strip().upper() or "NOSTATUS"
    return f"{dome_id}{status_part}"


class DomeStatusFinishSerializer(serializers.ModelSerializer):
    dome_name = serializers.CharField(source="dome.name", read_only=True)
    dome_code = serializers.CharField(source="dome.code", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = domeStatusFinish
        fields = [
            "id",
            "dome",
            "dome_code",
            "dome_name",
            "tonnage_dome",
            "status_dome",
            "description",
            "cek_duplicated",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "cek_duplicated",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate_status_dome(self, value):
        v = (value or "").strip().title()
        allowed = {"Finished", "Close", "Continue"}

        if not v:
            raise serializers.ValidationError("Status dome wajib diisi.")
        if v not in allowed:
            raise serializers.ValidationError(f"Status tidak valid. Allowed: {sorted(allowed)}")
        return v

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        dome_obj = attrs.get("dome") or getattr(self.instance, "dome", None)
        tonnage_dome = attrs.get("tonnage_dome", getattr(self.instance, "tonnage_dome", None))
        description = attrs.get("description", getattr(self.instance, "description", None))
        status_dome = attrs.get("status_dome", getattr(self.instance, "status_dome", None))

        if not dome_obj:
            raise serializers.ValidationError({"dome": "Dome wajib diisi."})
        if tonnage_dome is None:
            raise serializers.ValidationError({"tonnage_dome": "Tonnage dome wajib diisi."})
        if not description:
            raise serializers.ValidationError({"description": "Description wajib diisi."})
        if not status_dome:
            raise serializers.ValidationError({"status_dome": "Status dome wajib diisi."})

        if request and u and u.is_authenticated:
            allowed = user_allowed_iup_ids(u)
            dome_iup_id = getattr(dome_obj, "iup_id", None)

            if not (getattr(u, "is_system", False) or getattr(u, "is_superuser", False)):
                if allowed and dome_iup_id and int(dome_iup_id) not in allowed:
                    raise serializers.ValidationError({
                        "dome": "Dome tidak termasuk IUP yang diizinkan untuk user ini."
                    })

        cek_dup = build_dome_duplicate_key(dome_obj, status_dome)

        qs = domeStatusFinish.objects.filter(cek_duplicated=cek_dup)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": ["Data dome finish dengan status ini sudah ada."]
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        dome_obj = validated_data["dome"]
        status_dome = validated_data["status_dome"]

        validated_data["cek_duplicated"] = build_dome_duplicate_key(dome_obj, status_dome)

        instance = super().create(validated_data)

        self._sync_related(dome_obj.id, status_dome)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        dome_obj = validated_data.get("dome", instance.dome)
        status_dome = validated_data.get("status_dome", instance.status_dome)

        validated_data["cek_duplicated"] = build_dome_duplicate_key(dome_obj, status_dome)

        instance = super().update(instance, validated_data)

        self._sync_related(dome_obj.id, status_dome)
        return instance

    def _sync_related(self, dome_id, status_dome: str):
        if status_dome == "Finished":
            OreProductions.objects.filter(id_pile=dome_id).update(
                status_dome="Finished",
                pile_status="Close",
            )
            SourceMinesDome.objects.filter(id=dome_id).update(
                dome_finish="Finished",
                status_dome="Close",
            )
            SellingBarging.objects.filter(id_pile=dome_id).update(
                sale_dome="Finished"
            )
        elif status_dome == "Close":
            OreProductions.objects.filter(id_pile=dome_id).update(
                status_dome="Close",
                # pile_status="Close",
            )
            SourceMinesDome.objects.filter(id=dome_id).update(
                dome_finish="Close",
                status_dome="Close",
            )
            SellingBarging.objects.filter(id_pile=dome_id).update(
                sale_dome="Close"
            )
        elif status_dome == "Continue":
            OreProductions.objects.filter(id_pile=dome_id).update(
                status_dome="Continue",
                # pile_status="Continue",
            )
            SourceMinesDome.objects.filter(id=dome_id).update(
                dome_finish="Continue",
                status_dome="Continue",
            )
            SellingBarging.objects.filter(id_pile=dome_id).update(
                sale_dome='Continue'
            )