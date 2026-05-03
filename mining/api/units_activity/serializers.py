from rest_framework import serializers
from mining.models import HmUnit, HmUnitDetail

class HmUnitDetailSerializer(serializers.ModelSerializer):
    status_id = serializers.IntegerField(source="status.id", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)

    activity_id = serializers.IntegerField(source="activity.id", read_only=True)
    activity_name = serializers.CharField(source="activity.name", read_only=True)

    location_id = serializers.UUIDField(source="location.id", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = HmUnitDetail
        fields = [
            "id",
            "start_time",
            "end_time",
            "duration_min",
            "status",
            "status_id",
            "status_name",
            "activity",
            "activity_id",
            "activity_name",
            "location",
            "location_id",
            "location_name",
            "category",
            "description",
            "user_id",
            "username",
        ]

class HmUnitListSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    unit_id = serializers.UUIDField(source="unit.id", read_only=True)
    unit_code = serializers.CharField(source="unit.unit_code", read_only=True)
    unit_model = serializers.CharField(source="unit.unit_model", read_only=True)
    unit_vendor = serializers.CharField(source="unit.unit_vendor", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    total_details = serializers.IntegerField(read_only=True)
    total_duration_min = serializers.IntegerField(read_only=True)
    hm_total = serializers.SerializerMethodField()

    class Meta:
        model = HmUnit
        fields = [
            "id",
            "iup",
            "iup_code",
            "iup_name",
            "unit",
            "unit_id",
            "unit_code",
            "unit_model",
            "unit_vendor",
            "date",
            "shift",
            "hm_start",
            "hm_end",
            "hm_total",
            "total_details",
            "total_duration_min",
            "status",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def get_hm_total(self, obj):
        if obj.hm_start is None or obj.hm_end is None:
            return None
        return float(obj.hm_end) - float(obj.hm_start)

class HmUnitRetrieveSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    unit_id = serializers.UUIDField(source="unit.id", read_only=True)
    unit_code = serializers.CharField(source="unit.unit_code", read_only=True)
    unit_model = serializers.CharField(source="unit.unit_model", read_only=True)
    unit_vendor = serializers.CharField(source="unit.unit_vendor", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    hm_total = serializers.SerializerMethodField()
    details = HmUnitDetailSerializer(many=True, read_only=True)

    class Meta:
        model = HmUnit
        fields = [
            "id",
            "iup",
            "iup_code",
            "iup_name",
            "unit",
            "unit_id",
            "unit_code",
            "unit_model",
            "unit_vendor",
            "date",
            "shift",
            "hm_start",
            "hm_end",
            "hm_total",
            "status",
            "user_id",
            "username",
            "created_at",
            "updated_at",
            "details",
        ]

    def get_hm_total(self, obj):
        if obj.hm_start is None or obj.hm_end is None:
            return None
        return float(obj.hm_end) - float(obj.hm_start)

class HmUnitDetailWriteSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = HmUnitDetail
        fields = [
            "id",
            "start_time",
            "end_time",
            "duration_min",
            "status",
            "activity",
            "location",
            "category",
            "description",
        ]


class HmUnitWriteSerializer(serializers.ModelSerializer):
    details = HmUnitDetailWriteSerializer(many=True, required=False)

    class Meta:
        model = HmUnit
        fields = [
            "id",
            "iup",
            "unit",
            "date",
            "shift",
            "hm_start",
            "hm_end",
            "status",
            "details",
        ]

    def create(self, validated_data):
        details_data = validated_data.pop("details", [])
        request = self.context.get("request")

        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        hm_unit = HmUnit.objects.create(**validated_data)

        detail_objs = []
        for item in details_data:
            if request and request.user and request.user.is_authenticated:
                item["user"] = request.user
            detail_objs.append(HmUnitDetail(hm_unit=hm_unit, iup=hm_unit.iup, **item))

        if detail_objs:
            HmUnitDetail.objects.bulk_create(detail_objs)

        return hm_unit

    def update(self, instance, validated_data):
        details_data = validated_data.pop("details", None)
        request = self.context.get("request")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if details_data is not None:
            existing_map = {str(obj.id): obj for obj in instance.details.all()}
            sent_ids = set()

            for item in details_data:
                detail_id = str(item.get("id")) if item.get("id") else None

                if detail_id and detail_id in existing_map:
                    obj = existing_map[detail_id]
                    for attr, value in item.items():
                        if attr != "id":
                            setattr(obj, attr, value)
                    obj.iup = instance.iup
                    obj.save()
                    sent_ids.add(detail_id)
                else:
                    if request and request.user and request.user.is_authenticated:
                        item["user"] = request.user

                    new_obj = HmUnitDetail.objects.create(
                        hm_unit=instance,
                        iup=instance.iup,
                        **item,
                    )
                    sent_ids.add(str(new_obj.id))

            for obj_id, obj in existing_map.items():
                if obj_id not in sent_ids:
                    obj.delete()

        return instance