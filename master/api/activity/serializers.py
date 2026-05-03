from rest_framework import serializers
from master.models import MiningActivityCategories, MiningActivity


class MiningActivitySerializer(serializers.ModelSerializer):
    status_id = serializers.PrimaryKeyRelatedField(
        source="status",
        queryset=MiningActivityCategories.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    status_name = serializers.CharField(source="status.name", read_only=True)

    class Meta:
        model = MiningActivity
        fields = [
            "id",
            "code",
            "name",
            "status",
            "status_id",
            "status_name",
            "user",
        ]
        read_only_fields = ["user", "status"]

    def validate(self, attrs):
        code_value = attrs.get("code") or getattr(self.instance, "code", None)
        status_obj = attrs.get("status") or getattr(self.instance, "status", None)

        if code_value and status_obj:
            qs = MiningActivity.objects.filter(
                code=code_value,
                status=status_obj,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "non_field_errors": ["Data Activity sudah ada."]
                })

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class MiningActivityCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MiningActivityCategories
        fields = [
            "id",
            "code",
            "name",
            "user",
        ]
        read_only_fields = ["user"]

    def validate(self, attrs):
        code_value = attrs.get("code") or getattr(self.instance, "code", None)

        if code_value:
            qs = MiningActivityCategories.objects.filter(code=code_value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "non_field_errors": ["Code Activity Category sudah ada."]
                })

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)