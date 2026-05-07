from rest_framework import serializers
import re
from geology.models import SampleProductions,SamplesView
from master.models import SellingCode,StockFactories,Material,SampleMethod,SampleType

class SamplesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SamplesView
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",

            "date_sample",
            "shift",
            "type_sample",
            "sample_method",
            "material",
            "sampling_area",
            "sampling_point",
            "area_sampling",
            "factory_stock",
            "point_sampling",
            "selling_code",
            "batch",
            "increments",
            "size",
            "sample_weight",
            "sample_id",
            "remark",
            "primer_raw",
            "duplicate_raw",
            "sampling_desc",
            "code_batch",
            "no_sample",
            "user_id",
            "username",
            "created_at"
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

class SamplesCRUDSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    type_sample_label = serializers.CharField(source="id_type_sample.type_sample", read_only=True)
    sample_method_label = serializers.CharField(source="id_method.sample_method", read_only=True)

    material_label = serializers.SerializerMethodField()
    discharge_label = serializers.SerializerMethodField()
    product_code_label = serializers.SerializerMethodField()

    class Meta:
        model = SampleProductions
        fields = [
            "id",
            "iup", "iup_code", "iup_name",
            "tgl_sample",
            "shift",
            "id_type_sample", "type_sample_label",
            "id_method", "sample_method_label",
            "id_material", "material_label",
            "sampling_area",
            "sampling_point",
            "from_rl",
            "to_rl",
            "batch_code",
            "increments",
            "fraction",
            "size",
            "sample_weight",
            "sample_number",
            "remark",
            "primer_raw",
            "duplicate_raw",
            "to_its",
            "unit_truck",
            "kode_batch",
            "selling_pulp",
            "sampling_deskripsi",
            "type",
            "pile_original",
            "no_sample",
            "sample_dup",
            "discharge_area", "discharge_label",
            "product_code", "product_code_label",
            "user"
        ]
        read_only_fields = [
            "kode_batch",
            "type",
            "unit_truck",
            "iup_code",
            "iup_name",
            "type_sample_label",
            "sample_method_label",
            "material_label",
            "discharge_label",
            "product_code_label",
        ]
    
    def build_code(self, validated_data):
        iup = validated_data.get("iup")
        sample_number = validated_data.get("sample_number")

        iup_code = getattr(iup, "iup_code", f"IUP-{iup.id}")

        if sample_number:
            return f"{iup_code}-{sample_number}"

        return f"{iup_code}-UNKNOWN"
    
    def get_material_label(self, obj):
        if not obj.id_material:
            return None
        row = Material.objects.filter(id=obj.id_material).only("name").first()
        return row.name if row else None

    def get_discharge_label(self, obj):
        if not obj.discharge_area:
            return None
        row = StockFactories.objects.filter(id=obj.discharge_area).only("factory_stock").first()
        return row.factory_stock if row else None

    def get_product_code_label(self, obj):
        if not obj.product_code:
            return None
        row = SellingCode.objects.filter(id=obj.product_code).only("code").first()
        return row.code if row else None

    def get_sample_type(self, attrs):
        type_sample_id = attrs.get("id_type_sample", getattr(self.instance, "id_type_sample", None))
        if not type_sample_id:
            return None

        row = SampleType.objects.filter(id=type_sample_id).only("type_sample").first()
        return row.type_sample if row else None

    def get_method_name(self, attrs):
        method_id = attrs.get("id_method", getattr(self.instance, "id_method", None))
        if not method_id:
            return None

        row = SampleMethod.objects.filter(id=method_id).only("sample_method").first()
        return row.sample_method if row else None

    def get_truck_from_method(self, attrs):
        method_name = self.get_method_name(attrs)
        if not method_name:
            return None

        return re.sub(r"^(TS_|GRB_)", "", method_name)

    def extract_sample_dup(self, attrs):
        sampling_desc = attrs.get(
            "sampling_deskripsi",
            getattr(self.instance, "sampling_deskripsi", None)
        )

        if not sampling_desc:
            return None

        desc = str(sampling_desc).strip()
        if desc.upper().startswith("DUP_"):
            return desc[4:].strip()

        return None

    def get_material_name(self, attrs):
        material_id = attrs.get("id_material", getattr(self.instance, "id_material", None))
        if not material_id:
            return None

        row = Material.objects.filter(id=material_id).only("name").first()
        return row.name if row else None

    def get_discharge_name(self, attrs):
        discharge_id = attrs.get("discharge_area", getattr(self.instance, "discharge_area", None))
        if not discharge_id:
            return None

        row = StockFactories.objects.filter(id=discharge_id).only("factory_stock").first()
        return row.factory_stock if row else None

    
    def get_code_lot(self, attrs):
        product_code_id = attrs.get("product_code", getattr(self.instance, "product_code", None))
        if not product_code_id:
            return None

        row = SellingCode.objects.filter(id=product_code_id).only("code").first()
        return row.code if row else None

    
    def get_sample_category(self, attrs):
        type_sample_id = attrs.get("id_type_sample", getattr(self.instance, "id_type_sample", None))

        if not type_sample_id:
            return None

        row = SampleType.objects.filter(id=type_sample_id).only("category").first()
        return row.category if row else None

    def build_kode_batch(self, attrs):
        sample_type = attrs.get("type", getattr(self.instance, "type", None))
        sample_type_name = str(sample_type or "").upper()

        id_material = attrs.get("id_material", getattr(self.instance, "id_material", None))
        code_lot = self.get_code_lot(attrs)
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))

        if not sample_type_name or not id_material or not code_lot or not batch_code:
            return None

        return f"{sample_type_name}{id_material}{code_lot}{batch_code}"
    
    def build_selling_pulp(self, attrs):
        sample_type = attrs.get("type", getattr(self.instance, "type", None))
        sample_type_name = str(sample_type or "").upper()

        code_lot = self.get_code_lot(attrs)
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))

        if not sample_type_name or not code_lot or not batch_code:
            return None

        return f"{sample_type_name}{code_lot}{batch_code}"

    def build_sale_monitoring(self, attrs):
        
        sample_type = attrs.get("type", getattr(self.instance, "type", None))
        sample_type_name = str(sample_type or "").upper()

        id_material = attrs.get("id_material", getattr(self.instance, "id_material", None))
        code_lot = self.get_code_lot(attrs)
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))
        increments = attrs.get("increments", getattr(self.instance, "increments", None))

        if sample_type_name in {"LIS", "SAS"}:
            return None

        if not sample_type_name or not id_material or not code_lot or not batch_code:
            return None

        return f"{sample_type_name}{id_material}{code_lot}{batch_code}{increments or ''}"
        
    def validate(self, attrs):
        iup = attrs.get("iup") or getattr(self.instance, "iup", None)
        sample_number = attrs.get("sample_number", getattr(self.instance, "sample_number", None))

        sample_type = self.get_sample_type(attrs)
        attrs["type"] = sample_type

        unit_truck = self.get_truck_from_method(attrs)
        attrs["unit_truck"] = None

        qs = SampleProductions.objects.filter(
            iup=iup,
            is_deleted=False
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if sample_number and qs.filter(sample_number__iexact=sample_number).exists():
            raise serializers.ValidationError({
                "sample_number": f"Sample number '{sample_number}' already exists in this IUP."
            })

        sample_category = self.get_sample_category(attrs)

        generated_kode_batch = self.build_kode_batch(attrs)
        selling_pulp = self.build_selling_pulp(attrs)
        sale_monitoring = self.build_sale_monitoring(attrs)


        if str(sample_category or "").upper() == "SELLING":

            if not generated_kode_batch:
                raise serializers.ValidationError({
                    "batch_code": "Failed to generate kode batch for Selling sample. Check material, product code, and batch code."
                })

            if qs.filter(kode_batch__iexact=generated_kode_batch).exists():

                material_name = self.get_material_name(attrs) or "-"
                method_name = self.get_method_name(attrs) or "-"
                discharge_name = self.get_discharge_name(attrs) or "-"
                product_code_name = self.get_product_code_name(attrs) or "-"
                batch = attrs.get("batch_code", getattr(self.instance, "batch_code", None)) or "-"

                raise serializers.ValidationError({
                    "batch_code": (
                        f"Duplicate batch: "
                        f"{material_name}, {method_name}, {discharge_name}, {product_code_name} (Batch {batch})"
                    )
                })

            attrs["kode_batch"] = generated_kode_batch
            attrs["selling_pulp"] = selling_pulp
            attrs["sale_monitoring"] = sale_monitoring

        else:
            attrs["kode_batch"] = None
            attrs["selling_pulp"] = None
            attrs["sale_monitoring"] = None

        attrs["sample_dup"] = self.extract_sample_dup(attrs)
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        
        if not validated_data.get("code"):
            validated_data["code"] = self.build_code(validated_data)

        # return super().create(validated_data)
        instance = super().create(validated_data)

        return instance    
        # return super().create(validated_data)

    def update(self, instance, validated_data):
        u = self.context["request"].user
        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)
        return super().update(instance, validated_data)