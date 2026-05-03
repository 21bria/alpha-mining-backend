from rest_framework import serializers
from master.models import SampleType, SampleMethod


# =========================
# READ SERIALIZERS
# =========================

class SampleMethodSerializer(serializers.ModelSerializer):
    sample_type_id = serializers.IntegerField(source='sample_type.id', read_only=True)
    sample_type_name = serializers.CharField(source='sample_type.type_sample', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SampleMethod
        fields = [
            'id',
            'sample_type_id',
            'sample_type_name',
            'sample_method',
            'description',
            'status',
            'user',
            'user_name',
            'created_at',
            'updated_at',
        ]


class SampleTypeListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    total_methods = serializers.SerializerMethodField()

    class Meta:
        model = SampleType
        fields = [
            'id',
            'type_sample',
            'description',
            'status',
            'category',
            'user',
            'user_name',
            'created_at',
            'updated_at',
            'total_methods',
        ]

    def get_total_methods(self, obj):
        return obj.samplemethod_set.count()


class SampleTypeDetailSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    methods = SampleMethodSerializer(source='samplemethod_set', many=True, read_only=True)

    class Meta:
        model = SampleType
        fields = [
            'id',
            'type_sample',
            'description',
            'status',
            'category',
            'user',
            'user_name',
            'created_at',
            'updated_at',
            'methods',
        ]


# =========================
# WRITE SERIALIZERS
# =========================

class SampleTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleType
        fields = [
            'id',
            'type_sample',
            'description',
            'status',
            'category',
        ]

    def validate_type_sample(self, value):
        value = (value or "").strip()

        if not value:
            raise serializers.ValidationError("Type sample wajib diisi.")

        qs = SampleType.objects.filter(type_sample__iexact=value)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Type sample sudah ada.")

        return value

    def validate_category(self, value):
        if value is None:
            return value
        return value.strip()

    def validate_description(self, value):
        if value is None:
            return value
        return value.strip()

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().update(instance, validated_data)


class SampleMethodWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleMethod
        fields = [
            'id',
            'sample_type',
            'sample_method',
            'description',
            'status',
        ]

    def validate_sample_method(self, value):
        value = (value or "").strip()

        if not value:
            raise serializers.ValidationError("Sample method wajib diisi.")

        return value

    def validate_description(self, value):
        if value is None:
            return value
        return value.strip()

    def validate(self, attrs):
        sample_type = attrs.get("sample_type")
        sample_method = attrs.get("sample_method")

        # Saat update, kalau sample_type tidak dikirim, ambil dari instance
        if self.instance and sample_type is None:
            sample_type = self.instance.sample_type

        # Saat update, kalau sample_method tidak dikirim, ambil dari instance
        if self.instance and sample_method is None:
            sample_method = self.instance.sample_method

        if not sample_type:
            raise serializers.ValidationError({
                "sample_type": "Sample type wajib dipilih."
            })

        if not sample_method:
            raise serializers.ValidationError({
                "sample_method": "Sample method wajib diisi."
            })

        qs = SampleMethod.objects.filter(
            sample_type=sample_type,
            sample_method__iexact=sample_method.strip()
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "sample_method": f'Sample method "{sample_method}" sudah ada pada sample type "{sample_type.type_sample}".'
            })

        attrs["sample_method"] = sample_method.strip()
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().update(instance, validated_data)