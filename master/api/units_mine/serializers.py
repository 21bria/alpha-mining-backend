from rest_framework import serializers
from core.permissions import user_allowed_iup_ids
from master.models import MineUnits, UnitAssignment, unitsCategories, Vendors


def normalize_code(value: str | None) -> str:
    return (value or "").strip().upper().replace("_", "-").replace(" ", "-")


def build_unit_vendor(unit_code: str, vendor_code: str) -> str:
    u = normalize_code(unit_code)
    v = normalize_code(vendor_code)
    if not u:
        return ""
    if not v:
        return u
    return f"{u}-{v}"


class UnitsCategoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = unitsCategories
        fields = ["id", "category", "user", "created_at", "updated_at"]
        read_only_fields = ["user", "created_at", "updated_at"]

    def validate_category(self, value: str):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Category wajib diisi.")
        return v


class UnitAssignmentSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)
    unit_code = serializers.CharField(source="unit.unit_code", read_only=True)
    unit_vendor = serializers.CharField(source="unit.unit_vendor", read_only=True)

    class Meta:
        model = UnitAssignment
        fields = [
            "id",
            "unit",
            "unit_code",
            "unit_vendor",
            "iup",
            "iup_code",
            "iup_name",
            "start_date",
            "end_date",
            "active",
        ]

    def _pick_user_iup_id(self, user):
        iup_id = (
            getattr(user, "default_iup_id", None)
            or getattr(user, "active_iup_id", None)
            or getattr(user, "iup_id", None)
        )
        if iup_id:
            return int(iup_id)

        allowed = user_allowed_iup_ids(user) or set()
        one = next(iter(allowed), None)
        return int(one) if one else None

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if request and user and user.is_authenticated:
            if getattr(user, "is_site_user", False) and request.method in ("POST", "PUT", "PATCH"):
                iup_id = self._pick_user_iup_id(user)
                if not iup_id:
                    raise serializers.ValidationError({"iup": "User belum punya IUP aktif/default."})
                attrs["iup_id"] = iup_id

            if getattr(user, "is_management", False) and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(user) or set()
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({"iup": "IUP tidak termasuk allowed user ini."})

        unit = attrs.get("unit") or getattr(self.instance, "unit", None)
        active = attrs.get("active", getattr(self.instance, "active", True))

        if unit and active:
            qs = UnitAssignment.objects.filter(unit=unit, active=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "unit": "Unit ini sudah punya assignment aktif."
                })

        start_date = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end_date = attrs.get("end_date") if "end_date" in attrs else getattr(self.instance, "end_date", None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date tidak boleh lebih kecil dari start date."
            })

        return attrs


class MineUnitsSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField(read_only=True)
    vendor_name = serializers.SerializerMethodField(read_only=True)

    active_iup = serializers.SerializerMethodField(read_only=True)
    active_iup_code = serializers.SerializerMethodField(read_only=True)
    active_iup_name = serializers.SerializerMethodField(read_only=True)
    active_assignment_id = serializers.SerializerMethodField(read_only=True)
    active_assignment_start_date = serializers.SerializerMethodField(read_only=True)
    active_assignment_end_date = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MineUnits
        fields = [
            "id",
            "unit_vendor",
            "unit_code",
            "unit_model",
            "unit_class",
            "brand",
            "id_category",
            "category_name",
            "id_vendor",
            "vendor_name",
            "supports",
            "status",
            "description",
            "commisioning_date",
            "on_hire",
            "off_hire",
            "user",
            "created_at",
            "updated_at",
            "active_assignment_id",
            "active_iup",
            "active_iup_code",
            "active_iup_name",
            "active_assignment_start_date",
            "active_assignment_end_date",
        ]
        read_only_fields = [
            "unit_vendor",
            "user",
            "created_at",
            "updated_at",
            "active_assignment_id",
            "active_iup",
            "active_iup_code",
            "active_iup_name",
            "active_assignment_start_date",
            "active_assignment_end_date",
            "category_name",
            "vendor_name",
        ]

    def validate_unit_code(self, value: str):
        v = normalize_code(value)
        if not v:
            raise serializers.ValidationError("Unit code wajib diisi.")
        return v

    def validate_id_vendor(self, value):
        if not value:
            raise serializers.ValidationError("Vendor wajib diisi.")
        vendor = Vendors.objects.filter(pk=value).first()
        if not vendor:
            raise serializers.ValidationError("Vendor tidak ditemukan.")
        if not vendor.code:
            raise serializers.ValidationError(f"Vendor '{vendor.vendor_name}' belum punya code.")
        return value

    def validate(self, attrs):
        unit_code = attrs.get("unit_code", getattr(self.instance, "unit_code", None))
        id_vendor = attrs.get("id_vendor", getattr(self.instance, "id_vendor", None))

        if not unit_code:
            raise serializers.ValidationError({
                "unit_code": "Unit code wajib diisi."
            })

        if not id_vendor:
            raise serializers.ValidationError({
                "id_vendor": "Vendor wajib diisi."
            })

        vendor_obj = Vendors.objects.filter(pk=id_vendor).first()
        if not vendor_obj:
            raise serializers.ValidationError({
                "id_vendor": "Vendor tidak ditemukan."
            })

        if not vendor_obj.code:
            raise serializers.ValidationError({
                "id_vendor": f"Vendor '{vendor_obj.vendor_name}' belum punya code."
            })

        unit_code_norm = normalize_code(unit_code)
        unit_vendor = build_unit_vendor(unit_code_norm, vendor_obj.code)

        if not unit_vendor:
            raise serializers.ValidationError({
                "unit_code": "Gagal membentuk unit_vendor."
            })

        qs = MineUnits.objects.filter(unit_vendor__iexact=unit_vendor)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "unit_code": f"Unit '{unit_vendor}' sudah ada."
            })

        attrs["unit_code"] = unit_code_norm
        attrs["unit_vendor"] = unit_vendor
        return attrs

    def get_active_assignment(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {})
        assignments = prefetched.get("assignments")
        if assignments is not None:
            for a in assignments:
                if a.active:
                    return a

        return obj.assignments.select_related("iup").filter(active=True).order_by("-start_date").first()

    def get_active_assignment_id(self, obj):
        a = self.get_active_assignment(obj)
        return a.id if a else None

    def get_active_iup(self, obj):
        a = self.get_active_assignment(obj)
        return a.iup_id if a else None

    def get_active_iup_code(self, obj):
        a = self.get_active_assignment(obj)
        return a.iup.iup_code if a and a.iup else None

    def get_active_iup_name(self, obj):
        a = self.get_active_assignment(obj)
        return a.iup.iup_name if a and a.iup else None

    def get_active_assignment_start_date(self, obj):
        a = self.get_active_assignment(obj)
        return a.start_date if a else None

    def get_active_assignment_end_date(self, obj):
        a = self.get_active_assignment(obj)
        return a.end_date if a else None

    def get_category_name(self, obj):
        if not obj.id_category:
            return None
        cat = unitsCategories.objects.filter(pk=obj.id_category).first()
        return cat.category if cat else None

    def get_vendor_name(self, obj):
        if not obj.id_vendor:
            return None
        vendor = Vendors.objects.filter(pk=obj.id_vendor).first()
        return vendor.vendor_name if vendor else None

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user
        return MineUnits.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance