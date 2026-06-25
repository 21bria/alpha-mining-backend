from django.db import transaction
from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum
from mining.models import mineProductions
from geology.models import OreProductions
from selling.models import SellingBargingAdjustment,SellingBarging

# Barging      : tetap update semua data code_lot
# Geology      : update hanya direct = Yes, kalau ada data direct
# Mining       : update hanya direct = Yes, kalau ada data direct
# Validasi     : jumlah direct Yes geology/mining harus sama dengan jumlah direct Yes barging
# Pembagian    : tonnage_adjust / ritase_direct_barging

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

    def _apply_adjustment_to_related_tables(
        self,
        *,
        code_lot_obj,
        ritase_ori,
        tonnage_adjust,
        date_arrival,
        date_departure,
    ):
        # =========================
        # BARGING
        # =========================
        barging_qs = SellingBarging.objects.filter(
            code_lot__iexact=code_lot_obj.code
        )

        if not barging_qs.exists():
            raise serializers.ValidationError({
                "code_lot": f"Data barging untuk {code_lot_obj.code} tidak ditemukan."
            })

        total_barging_count = barging_qs.count()

        if total_barging_count <= 0:
            raise serializers.ValidationError({
                "ritase_ori": "Ritase barging tidak valid."
            })

        barging_direct_qs = barging_qs.filter(
            direct__iexact="Yes"
        )

        barging_direct_count = barging_direct_qs.count()

        # pembagian harus dari total ritase barging,
        # supaya total barging balance dengan tonnage_adjust
        tonnage_per_ritase = (
            Decimal(str(tonnage_adjust)) / Decimal(str(total_barging_count))
        )

        # update semua barging dalam code lot
        barging_qs.update(
            tonnage=tonnage_per_ritase,
            date_barge_in=date_arrival,
            date_barge_out=date_departure,
            status_barging="Complete",
        )

        # kalau tidak ada direct Yes di barging,
        # geology dan mining tidak ikut update
        if barging_direct_count <= 0:
            return

        # =========================
        # AMBIL ID PILE DARI BARGING
        # =========================
        barging_ref = (
            barging_qs
            .exclude(id_pile__isnull=True)
            .first()
        )

        if not barging_ref:
            return

        id_pile = barging_ref.id_pile
        dome_id = id_pile

        # =========================
        # GEOLOGY
        # =========================
        geology_qs = OreProductions.objects.filter(
            id_pile=id_pile,
            direct__iexact="Yes",
        )

        # geology_count = geology_qs.count()

        # if geology_count > 0:
        #     if geology_count != barging_direct_count:
        #         raise serializers.ValidationError({
        #             "ritase_ori": (
        #                 f"Direct geology ({geology_count}) "
        #                 f"tidak sama dengan direct barging ({barging_direct_count})"
        #             )
        #         })

        #     geology_qs.update(
        #         tonnage=tonnage_per_ritase
        #     )

        geology_total = geology_qs.aggregate(
            total_ritase=Sum("ritase"),
        )

        geology_ritase = int(geology_total["total_ritase"] or 0)

        if geology_ritase > 0:
            if geology_ritase != barging_direct_count:
                raise serializers.ValidationError({
                    "ritase_ori": (
                        f"Ritase direct geology ({geology_ritase}) "
                        f"tidak sama dengan direct barging ({barging_direct_count})"
                    )
                })

            for geo in geology_qs:
                geo_ritase = Decimal(str(geo.ritase or 0))
                geo.tonnage = tonnage_per_ritase * geo_ritase
                geo.save(update_fields=["tonnage"])
                

        # =========================
        # MINING
        # =========================
        mining_qs = mineProductions.objects.filter(
            dome_id=dome_id,
            direct__iexact="Yes",
        )

        mining_count = mining_qs.count()

        if mining_count > 0:
            if mining_count != barging_direct_count:
                raise serializers.ValidationError({
                    "ritase_ori": (
                        f"Direct mining ({mining_count}) "
                        f"tidak sama dengan direct barging ({barging_direct_count})"
                    )
                })

            mining_qs.update(
                tonnage=tonnage_per_ritase
            )

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

        existing = SellingBargingAdjustment.objects.filter(
            code_lot=code_lot_obj
        ).first()

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

            self._apply_adjustment_to_related_tables(
                code_lot_obj=code_lot_obj,
                ritase_ori=ritase_ori,
                tonnage_adjust=tonnage_adjust,
                date_arrival=date_arrival,
                date_departure=date_departure,
            )

            return existing

        obj = super().create(validated_data)

        self._apply_adjustment_to_related_tables(
            code_lot_obj=code_lot_obj,
            ritase_ori=ritase_ori,
            tonnage_adjust=tonnage_adjust,
            date_arrival=date_arrival,
            date_departure=date_departure,
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

        self._apply_adjustment_to_related_tables(
            code_lot_obj=code_lot_obj,
            ritase_ori=ritase_ori,
            tonnage_adjust=tonnage_adjust,
            date_arrival=date_arrival,
            date_departure=date_departure,
        )

        return obj