from django.db import transaction
from rest_framework import serializers
from selling.models import SellingBargingTemporaryView, SellingBargingTemporary
from master.models import Material, SourceMinesDome,MineIUP,BargeUnits,SellingCode
from datetime import datetime

def build_selling_code(iup_code: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{iup_code}-{ts}"

class SellingBargingTemporarySerializer(serializers.ModelSerializer):
    tonnage = serializers.SerializerMethodField()

    class Meta:
        model = SellingBargingTemporaryView
        fields = [
            "id",
            "iup_id",
            "iup_code",
            "iup_name",

            "date_hauling",
            "time_hauling",
            "barge_code",
            "shift",
            "dome",
            "stockpile",
            "material",
            "unit_code",
            "tonnage",
            "code_lot",
            "code_inc",
            "code_sub",
            "type_selling",
            "sale_adjust",
            "no_urut",
            "description",
            "status",
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

class SellingBargingTemporaryWriteSerializer(serializers.ModelSerializer):
    iup = serializers.PrimaryKeyRelatedField(
        queryset=MineIUP.objects.all(),
        required=False,
        allow_null=True,
    )
    id_material = serializers.IntegerField(required=True)
    id_pile = serializers.IntegerField(required=True)
    barge_code = serializers.IntegerField(required=True)
    code_lot = serializers.IntegerField(required=True)

    class Meta:
        model = SellingBargingTemporary
        fields = [
            "id",
            "iup",
            "date_hauling",
            "time_hauling",
            "shift",
            "id_material",
            "id_pile",
            "unit_code",
            "code_sub",
            "code_lot",
            "barge_code",
            "description",
        ]

    def validate(self, attrs):
        required_messages = {
            "date_hauling": "Date harus diisi.",
            "shift": "Shift harus diisi.",
            "id_material": "Material harus diisi.",
            "id_pile": "Dome harus diisi.",
            "unit_code": "Truck harus diisi.",
            "code_sub": "SubLot harus diisi.",
            "code_lot": "Code Lot harus diisi.",
            "barge_code": "Tongkang harus diisi.",
        }

        for field, message in required_messages.items():
            value = attrs.get(field)
            if value in [None, ""]:
                raise serializers.ValidationError({field: message})

        return attrs

    def _get_iup(self, validated_data):
        iup = validated_data.get("iup")
        request = self.context.get("request")

        if iup:
            return iup

        if request and getattr(request.user, "active_iup_id", None):
            return MineIUP.objects.filter(id=request.user.active_iup_id).first()

        if request and getattr(request.user, "iup_id", None):
            return MineIUP.objects.filter(id=request.user.iup_id).first()

        return None

    def _resolve_material_and_sale(self, id_material):
        material_obj = Material.objects.filter(id=id_material).first()
        if not material_obj:
            raise serializers.ValidationError({"id_material": "Material tidak ditemukan."})

        material_name = (getattr(material_obj, "name", None) or "").upper()

        if material_name == "LIM":
            return material_obj, "LIS", "HPAL"
        elif material_name == "SAP":
            return material_obj, "SAS", "SAP"

        return material_obj, None, None

    def _resolve_dome_and_stockpile(self, id_pile):
        dome_obj = SourceMinesDome.objects.filter(id=id_pile).first()
        if not dome_obj:
            raise serializers.ValidationError({"id_pile": "Dome tidak ditemukan."})

        if not dome_obj.dumping_id:
            raise serializers.ValidationError(
                {"id_pile": "Dome tidak memiliki stockpile/dumping."}
            )

        return dome_obj, dome_obj.dumping_id

    def create(self, validated_data):
        request = self.context["request"]

        iup = self._get_iup(validated_data)
        id_material = validated_data["id_material"]
        id_pile = validated_data["id_pile"]
        code_lot = validated_data["code_lot"]
        date_hauling = validated_data["date_hauling"]

        _, type_selling, sale_adjust = self._resolve_material_and_sale(id_material)
        _, id_stockpile = self._resolve_dome_and_stockpile(id_pile)

        no_urut = (
            SellingBargingTemporary.objects
            .filter(date_hauling=date_hauling, iup=iup)
            .count()
        ) + 1

        count_lot = (
            SellingBargingTemporary.objects
            .filter(code_lot=code_lot, iup=iup)
            .count()
        )
        code_sub_auto = f"SL_{(count_lot // 100 + 1):02d}"

        count_inc = (
            SellingBargingTemporary.objects
            .filter(code_lot=code_lot, code_sub_auto=code_sub_auto, iup=iup)
            .count()
        )
        code_inc = (count_inc // 20) + 1

        # ambil iup_code
        iup_code = iup.iup_code if iup else "NOIUP"

        # generate code unik
        generated_code = build_selling_code(iup_code)

        return SellingBargingTemporary.objects.create(
            iup=iup,
            date_hauling=validated_data["date_hauling"],
            time_hauling=validated_data.get("time_hauling"),
            shift=validated_data["shift"],
            id_material=id_material,
            id_pile=id_pile,
            id_stockpile=id_stockpile,
            unit_code=validated_data["unit_code"],
            code_sub=validated_data["code_sub"],
            code_lot=code_lot,
            barge_code=validated_data["barge_code"],
            tonnage=30.79,
            no_urut=no_urut,
            type_selling=type_selling,
            sale_adjust=sale_adjust,
            code_inc=code_inc,
            code_sub_auto=code_sub_auto,
            id_user=request.user.id if request.user.is_authenticated else None,
            user=request.user if request.user.is_authenticated else None,
            description=validated_data.get("description"),
            code=generated_code,
        )

    def update(self, instance, validated_data):
        request = self.context["request"]

        iup = validated_data.get("iup", instance.iup)
        id_material = validated_data.get("id_material", instance.id_material)
        id_pile = validated_data.get("id_pile", instance.id_pile)

        _, type_selling, sale_adjust = self._resolve_material_and_sale(id_material)
        _, id_stockpile = self._resolve_dome_and_stockpile(id_pile)

        instance.iup = iup or instance.iup
        instance.date_hauling = validated_data.get("date_hauling", instance.date_hauling)
        instance.time_hauling = validated_data.get("time_hauling", instance.time_hauling)
        instance.shift = validated_data.get("shift", instance.shift)
        instance.id_material = id_material
        instance.id_pile = id_pile
        instance.id_stockpile = id_stockpile
        instance.unit_code = validated_data.get("unit_code", instance.unit_code)
        instance.code_sub = validated_data.get("code_sub", instance.code_sub)
        instance.code_lot = validated_data.get("code_lot", instance.code_lot)
        instance.barge_code = validated_data.get("barge_code", instance.barge_code)
        instance.type_selling = type_selling
        instance.sale_adjust = sale_adjust
        instance.description = validated_data.get("description", instance.description)
        instance.id_user = request.user.id if request.user.is_authenticated else instance.id_user
        instance.user = request.user if request.user.is_authenticated else instance.user
        instance.save()
        return instance

class SellingBargingTemporaryDetailSerializer(serializers.ModelSerializer):
    iup = serializers.IntegerField(source="iup_id", read_only=True)
    iup_id = serializers.IntegerField(read_only=True)
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    material_name = serializers.SerializerMethodField()
    dome_name = serializers.SerializerMethodField()
    barge_name = serializers.SerializerMethodField()
    code_lot_label = serializers.SerializerMethodField()

    class Meta:
        model = SellingBargingTemporary
        fields = "__all__"

    def get_material_name(self, obj):
        from master.models import Material
        m = Material.objects.filter(id=obj.id_material).first()
        return m.name if m else None

    def get_dome_name(self, obj):
        from master.models import SourceMinesDome
        d = SourceMinesDome.objects.filter(id=obj.id_pile).first()
        return d.pile_id if d else None

    def get_barge_name(self, obj):
        from master.models import BargeUnits
        b = BargeUnits.objects.filter(id=obj.barge_code).first()
        return b.barge_code if b else None

    def get_code_lot_label(self, obj):
        from master.models import SellingCode

        # kalau DB simpan id
        by_id = SellingCode.objects.filter(id=obj.code_lot).first()
        if by_id:
            return by_id.code

        # fallback kalau simpan string
        by_code = SellingCode.objects.filter(code=obj.code_lot).first()
        return by_code.code if by_code else obj.code_lot