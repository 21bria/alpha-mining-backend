from django.db import transaction
from rest_framework import serializers

from selling.models import SellingBargingAdjustment,SellingBarging

class SellingBargingAdjustmentSerializer(serializers.ModelSerializer):
    code_lot_code = serializers.CharField(source="code_lot.code", read_only=True)

    iup_id = serializers.IntegerField(source="code_lot.iup.id", read_only=True)
    iup_code = serializers.CharField(source="code_lot.iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="code_lot.iup.iup_name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SellingBargingAdjustment
        fields = [
            "id",
            "code_lot",
            "code_lot_code",
            "iup_id",
            "iup_code",
            "iup_name",
            "date_arrival",
            "date_departure",
            "jetty_departure",
            "ritase_ori",
            "tonnage_ori",
            "tonnage_adjust",
            "status",
            "description",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        code_lot = attrs.get("code_lot") or getattr(instance, "code_lot", None)
        ritase_ori = attrs.get("ritase_ori", getattr(instance, "ritase_ori", None))
        tonnage_ori = attrs.get("tonnage_ori", getattr(instance, "tonnage_ori", None))
        tonnage_adjust = attrs.get("tonnage_adjust", getattr(instance, "tonnage_adjust", None))
        date_arrival = attrs.get("date_arrival", getattr(instance, "date_arrival", None))
        date_departure = attrs.get("date_departure", getattr(instance, "date_departure", None))
        jetty_departure = attrs.get("jetty_departure", getattr(instance, "jetty_departure", None))

        errors = {}

        if not code_lot:
            errors["code_lot"] = "Code Lot is required."

        if ritase_ori in [None, ""]:
            errors["ritase_ori"] = "Ritase is required."
        elif int(ritase_ori) <= 0:
            errors["ritase_ori"] = "Ritase must be greater than 0."

        if tonnage_ori in [None, ""]:
            errors["tonnage_ori"] = "Tonnage is required."
        elif float(tonnage_ori) <= 0:
            errors["tonnage_ori"] = "Tonnage must be greater than 0."

        if not date_arrival:
            errors["date_arrival"] = "Arrival is required."

        if not date_departure:
            errors["date_departure"] = "Departure is required."

        if not jetty_departure:
            errors["jetty_departure"] = "Jetty is required."

        if tonnage_adjust in [None, ""]:
            errors["tonnage_adjust"] = "Adjustment Tonnage is required."
        elif float(tonnage_adjust) <= 0:
            errors["tonnage_adjust"] = "Adjustment Tonnage must be greater than 0."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        code_lot_obj = validated_data["code_lot"]

        ritase_ori = validated_data["ritase_ori"]
        date_arrival = validated_data["date_arrival"]
        date_departure = validated_data["date_departure"]
        tonnage_adjust = validated_data["tonnage_adjust"]

        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        validated_data["status"] = "Complete"

        tonnage_per_ritase = (tonnage_adjust / ritase_ori) if ritase_ori > 0 else 0

        existing = SellingBargingAdjustment.objects.filter(code_lot=code_lot_obj).first()

        if existing:
            existing.date_arrival = validated_data.get("date_arrival")
            existing.date_departure = validated_data.get("date_departure")
            existing.jetty_departure = validated_data.get("jetty_departure")
            existing.ritase_ori = validated_data.get("ritase_ori")
            existing.tonnage_ori = validated_data.get("tonnage_ori")
            existing.tonnage_adjust = validated_data.get("tonnage_adjust")
            existing.description = validated_data.get("description")
            existing.status = "Complete"
            existing.user = validated_data.get("user")
            existing.save()

            SellingBarging.objects.filter(code_lot=code_lot_obj.code).update(
                tonnage=tonnage_per_ritase,
                date_barge_in=date_arrival,
                date_barge_out=date_departure,
                status_barging="Complete",
            )
            return existing

        obj = super().create(validated_data)

        SellingBarging.objects.filter(code_lot=code_lot_obj.code).update(
            tonnage=tonnage_per_ritase,
            date_barge_in=date_arrival,
            date_barge_out=date_departure,
            status_barging="Complete",
        )

        return obj

    @transaction.atomic
    def update(self, instance, validated_data):
        ritase_ori = validated_data.get("ritase_ori", instance.ritase_ori)
        tonnage_adjust = validated_data.get("tonnage_adjust", instance.tonnage_adjust)
        date_arrival = validated_data.get("date_arrival", instance.date_arrival)
        date_departure = validated_data.get("date_departure", instance.date_departure)
        code_lot_obj = validated_data.get("code_lot", instance.code_lot)

        validated_data["status"] = "Complete"

        obj = super().update(instance, validated_data)

        tonnage_per_ritase = (tonnage_adjust / ritase_ori) if ritase_ori and ritase_ori > 0 else 0

        SellingBarging.objects.filter(code_lot=code_lot_obj.code).update(
            tonnage=tonnage_per_ritase,
            date_barge_in=date_arrival,
            date_barge_out=date_departure,
            status_barging="Complete",
        )

        return obj