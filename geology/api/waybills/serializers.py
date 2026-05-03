from rest_framework import serializers
from datetime import datetime
import re

from django.utils import timezone
from geology.models import Waybills,listWaybills

class WaybillsSerializer(serializers.ModelSerializer):
    # delivery_display = serializers.SerializerMethodField()

    class Meta:
        model = listWaybills
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",

            "tgl_deliver",
            "delivery_time",
            "waybill_number",

            "qty",
            "sample_id",
            "sample_status",
            "mral_order",
            "roa_order",
            "remarks",
            "user_id",
            "username"

        ]

    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    # def get_delivery_display(self, obj):
    #     if not obj.delivery:
    #         return "-"
    #     dt = timezone.localtime(obj.delivery)
    #     return dt.strftime("%d-%m-%Y %H:%M")


def clean_code_part(value: str) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    return s


class WaybillsCRUDSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = Waybills
        fields = [
            "id",
            "code",
            "iup", "iup_code", "iup_name",
            "tgl_deliver",
            "delivery_time",
            "waybill_number",
            "qty",
            "sample_id",
            "mral_order",
            "roa_order",
            "remarks",
            "delivery",
            "user_id",
            "username",
        ]
        read_only_fields = [
            "code",
            "delivery",
            "user_id",
            "username",
            "iup_code",
            "iup_name",
        ]

    def validate(self, attrs):
        iup_obj = attrs.get("iup") or getattr(self.instance, "iup", None)
        sample_id = attrs.get("sample_id") or getattr(self.instance, "sample_id", None)
        tgl_deliver = attrs.get("tgl_deliver") or getattr(self.instance, "tgl_deliver", None)
        delivery_time = attrs.get("delivery_time") or getattr(self.instance, "delivery_time", None)

        if not iup_obj:
            raise serializers.ValidationError({"iup": "IUP is required."})

        if not sample_id:
            raise serializers.ValidationError({"sample_id": "Sample ID is required."})

        qs = Waybills.objects.filter(
            iup=iup_obj,
            sample_id=sample_id,
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Data waybill sudah ada untuk IUP '{iup_obj.iup_code}' dan sample_id '{sample_id}'."
                ]
            })

        if tgl_deliver and not delivery_time:
            raise serializers.ValidationError({
                "delivery_time": "Delivery time is required when tgl_deliver is filled."
            })

        if delivery_time and not tgl_deliver:
            raise serializers.ValidationError({
                "tgl_deliver": "Delivery date is required when delivery_time is filled."
            })

        return attrs

    def _build_delivery_datetime(self, tgl_deliver, delivery_time):
        if not tgl_deliver or not delivery_time:
            return None

        dt = datetime.combine(tgl_deliver, delivery_time)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def _build_code(self, iup_obj, tgl_deliver, sample_id):
        iup_code = clean_code_part(getattr(iup_obj, "iup_code", None) or "NOIUP")
        d = tgl_deliver.strftime("%Y%m%d") if tgl_deliver else "NODATE"
        sample = clean_code_part(sample_id or "NOSAMPLE")
        return f"WBL-{iup_code}-{d}-{sample}"

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        iup_obj = validated_data.get("iup")
        tgl_deliver = validated_data.get("tgl_deliver")
        delivery_time = validated_data.get("delivery_time")
        sample_id = validated_data.get("sample_id")

        validated_data["delivery"] = self._build_delivery_datetime(tgl_deliver, delivery_time)
        validated_data["code"] = self._build_code(iup_obj, tgl_deliver, sample_id)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        iup_obj = validated_data.get("iup", instance.iup)
        tgl_deliver = validated_data.get("tgl_deliver", instance.tgl_deliver)
        delivery_time = validated_data.get("delivery_time", instance.delivery_time)
        sample_id = validated_data.get("sample_id", instance.sample_id)

        validated_data["delivery"] = self._build_delivery_datetime(tgl_deliver, delivery_time)
        validated_data["code"] = self._build_code(iup_obj, tgl_deliver, sample_id)

        return super().update(instance, validated_data)