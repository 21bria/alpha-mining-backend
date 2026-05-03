from rest_framework import serializers
from rest_framework import serializers
from selling.models import SellingDetailsBargingView,SellingBarging


class SellingBargingSerializer(serializers.ModelSerializer):
    tonnage = serializers.SerializerMethodField()
    ton_barge_load = serializers.SerializerMethodField()
    ton_barge_unload = serializers.SerializerMethodField()
    fill_adjust = serializers.SerializerMethodField()

    class Meta:
        model = SellingDetailsBargingView
        fields = [
            "id",

            "iup_id",
            "iup_code",
            "iup_name",

            "date_barge_in",
            "date_barge_out",
            "barge_code",
            "shift",
            "dome",
            "stockpile",
            "material",
            "unit_code",
            "ritase",

            "tonnage",
            "ton_barge_load",
            "ton_barge_unload",
            "fill_adjust",

            "batch",
            "code_inc",
            "code_sub",
            "code_batch_in",
            "code_batch_ex",
            "code_batch_pulp",
            "surv_order",
            "code_fix_batch",
            "code_lot",
            "factory_stock",
            "type_selling",
            "date_hauling",
            "time_hauling",
            "no_input",
            "sale_adjust",
            "sale_dome",
            "status_barging",
            "direct",
            "description",

            "user_id",
            "username",
            "created_at",
        ]

    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_tonnage(self, obj):
        return self._fmt_decimal(obj.tonnage)

    def get_ton_barge_load(self, obj):
        return self._fmt_decimal(obj.ton_barge_load)

    def get_ton_barge_unload(self, obj):
        return self._fmt_decimal(obj.ton_barge_unload)

    def get_fill_adjust(self, obj):
        return self._fmt_decimal(obj.fill_adjust)

class SellingBargingImportDeleteSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SellingBarging
        fields = [
            "id",
            "iup_id",
            "iup_code",
            "iup_name",
            "username",
            "date_hauling",
            "barge_code",
            "code_lot",
            "created_at",
        ]
        read_only_fields = fields