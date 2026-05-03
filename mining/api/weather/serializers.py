from rest_framework import serializers
from datetime import datetime, timedelta
from mining.models import Weather
from master.models import MineIUP
from core.permissions import user_allowed_iup_ids

class WeatherSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    ALLOWED_CATEGORIES = {"Rainy", "Slippery"}

    class Meta:
        model = Weather
        fields = [
            "id",
            "code",
            "iup", "iup_code", "iup_name",
            "date",
            "shift",
            "category",
            "start_time",
            "end_time",
            "duration",
            "description",
            "user",
        ]
        read_only_fields = ["user", "duration", "code"]

    def _build_code(self, iup_obj, date_value, shift, category, start_time, end_time):
        iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
        d = date_value.strftime("%Y%m%d") if date_value else "NODATE"

        st = start_time.strftime("%H%M") if start_time else "0000"
        et = end_time.strftime("%H%M") if end_time else "0000"

        shift_val = (shift or "").strip().upper().replace(" ", "")
        cat_val = (category or "").strip().upper().replace(" ", "")

        return f"WTH-{iup_code}-{d}-{shift_val}-{cat_val}-{st}-{et}"

    def validate(self, attrs):
        request = self.context.get("request")
        u = getattr(request, "user", None)

        # ambil nilai final (buat create/update)
        iup_obj = attrs.get("iup") or getattr(self.instance, "iup", None)
        date_value = attrs.get("date") or getattr(self.instance, "date", None)
        shift = attrs.get("shift") or getattr(self.instance, "shift", None)
        category = attrs.get("category") or getattr(self.instance, "category", None)
        start_time = attrs.get("start_time") or getattr(self.instance, "start_time", None)
        end_time = attrs.get("end_time") or getattr(self.instance, "end_time", None)

        if category and category not in self.ALLOWED_CATEGORIES:
            raise serializers.ValidationError({
                "category": f"Category harus salah satu dari: {', '.join(sorted(self.ALLOWED_CATEGORIES))}"
            })

        if request and u and u.is_authenticated:
            if u.is_site_user and request.method in ("POST", "PUT", "PATCH"):
                if not u.default_iup_id:
                    raise serializers.ValidationError({"iup": "User belum punya default IUP."})
                attrs["iup_id"] = int(u.default_iup_id)
                if not iup_obj:
                    iup_obj = getattr(self.instance, "iup", None)
                    if not iup_obj and hasattr(Weather, "iup"):
                        # nanti create() akan pakai iup_id, untuk validasi duplikat cukup pakai iup_id bila perlu
                        pass

            if u.is_management and "iup" in attrs and attrs["iup"] is not None:
                allowed = user_allowed_iup_ids(u)
                if int(attrs["iup"].id) not in allowed:
                    raise serializers.ValidationError({"iup": "IUP tidak termasuk allowed untuk user ini."})

        # hitung duration otomatis
        if start_time and end_time and date_value:
            start_dt = datetime.combine(date_value, start_time)
            end_dt = datetime.combine(date_value, end_time)

            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            diff = end_dt - start_dt
            duration_hours = round(diff.total_seconds() / 3600, 2)
            attrs["duration"] = duration_hours

        # validasi duplikasi kombinasi utama
        iup_id = None
        if "iup_id" in attrs:
            iup_id = attrs["iup_id"]
        elif iup_obj is not None:
            iup_id = getattr(iup_obj, "id", None)

        if iup_id and date_value and shift and category and start_time and end_time:
            qs = Weather.objects.filter(
                iup_id=iup_id,
                date=date_value,
                shift=shift,
                category=category,
                start_time=start_time,
                end_time=end_time,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "non_field_errors": [
                        "Data weather dengan kombinasi IUP, date, shift, category, start time, dan end time sudah ada."
                    ]
                })

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user

        iup_obj = validated_data.get("iup")
        if not iup_obj and validated_data.get("iup_id"):
            iup_obj = MineIUP.objects.filter(id=validated_data["iup_id"]).first()

        validated_data["code"] = self._build_code(
            iup_obj=iup_obj,
            date_value=validated_data.get("date"),
            shift=validated_data.get("shift"),
            category=validated_data.get("category"),
            start_time=validated_data.get("start_time"),
            end_time=validated_data.get("end_time"),
        )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user

        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)

        iup_obj = validated_data.get("iup", instance.iup)

        validated_data["code"] = self._build_code(
            iup_obj=iup_obj,
            date_value=validated_data.get("date", instance.date),
            shift=validated_data.get("shift", instance.shift),
            category=validated_data.get("category", instance.category),
            start_time=validated_data.get("start_time", instance.start_time),
            end_time=validated_data.get("end_time", instance.end_time),
        )

        return super().update(instance, validated_data)