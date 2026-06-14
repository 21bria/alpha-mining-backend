from rest_framework import serializers
import re
from geology.models import SampleProductions,SamplesView
from master.models import SourceMinesDumping,SourceMinesDome,Material,SampleMethod,SampleType

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

    sampling_area_label = serializers.SerializerMethodField()
    sampling_point_label = serializers.SerializerMethodField()

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

            "sampling_area", "sampling_area_label",
            "sampling_point", "sampling_point_label",

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
            "discharge_area",
            "product_code",
            "user"
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

    def get_sampling_area_label(self, obj):
        if not obj.sampling_area:
            return None
        
        row = SourceMinesDumping.objects.filter(id=obj.sampling_area).only("dumping_point").first()
        return row.dumping_point if row else None

    def get_sampling_point_label(self, obj):
        if not obj.sampling_point:
            return None
        row = SourceMinesDome.objects.filter(id=obj.sampling_point).only("pile_id").first()
        return row.pile_id if row else None
    
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

        desc = sampling_desc.strip()

        if desc.upper().startswith("DUP_"):
            return desc[4:]   # hapus DUP_

        return None

    def get_material_name(self, attrs):
        material_id = attrs.get("id_material", getattr(self.instance, "id_material", None))
        if not material_id:
            return None

        row = Material.objects.filter(id=material_id).only("name").first()
        return row.name if row else None


    def get_sampling_area_name(self, attrs):
        sampling_area_id = attrs.get("sampling_area", getattr(self.instance, "sampling_area", None))
        if not sampling_area_id:
            return None

        row = SourceMinesDumping.objects.filter(id=sampling_area_id).only("dumping_point").first()
        return row.dumping_point if row else None


    def get_sampling_point_name(self, attrs):
        sampling_point_id = attrs.get("sampling_point", getattr(self.instance, "sampling_point", None))
        if not sampling_point_id:
            return None

        row = SourceMinesDome.objects.filter(id=sampling_point_id).only("pile_id").first()
        return row.pile_id if row else None


    def build_kode_batch(self, attrs):
        sample_type = attrs.get("type", getattr(self.instance, "type", None))

        if str(sample_type or "").upper() != "PDS":
            return None

        id_material = attrs.get("id_material", getattr(self.instance, "id_material", None))
        unit_truck = attrs.get("unit_truck", getattr(self.instance, "unit_truck", None))
        sampling_area = attrs.get("sampling_area", getattr(self.instance, "sampling_area", None))
        sampling_point = attrs.get("sampling_point", getattr(self.instance, "sampling_point", None))
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))

        if not id_material or not unit_truck or not sampling_area or not sampling_point or not batch_code:
            return None

        return f"PDS{id_material}{unit_truck}{sampling_area}{sampling_point}{batch_code}"
    
    def build_kode_psi(self, attrs):
        sample_type = attrs.get("type", getattr(self.instance, "type", None))

        if str(sample_type or "").upper() != "PSI":
            return None

        id_material = attrs.get("id_material", getattr(self.instance, "id_material", None))
        sampling_point = attrs.get("sampling_point", getattr(self.instance, "sampling_point", None))
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))

        if not id_material  or not sampling_point or not batch_code:
            return None

        return f"PSI{id_material}{sampling_point}{batch_code}"


    def validate(self, attrs):
        iup = attrs.get("iup") or getattr(self.instance, "iup", None)
        sample_number = attrs.get("sample_number", getattr(self.instance, "sample_number", None))

        # auto isi type dari sample type
        sample_type = self.get_sample_type(attrs)
        attrs["type"] = sample_type

        # auto isi unit_truck dari sample method
        unit_truck = self.get_truck_from_method(attrs)
        attrs["unit_truck"] = unit_truck


        qs = SampleProductions.objects.filter(
            iup=iup,
            is_deleted=False
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if sample_number:
            if qs.filter(sample_number__iexact=sample_number).exists():
                raise serializers.ValidationError({
                    "sample_number": f"Sample number '{sample_number}' already exists in this IUP."
                })

        generated_kode_batch = self.build_kode_batch(attrs)
        generated_kode_psi = self.build_kode_psi(attrs)

        if str(sample_type or "").upper() == "PDS":
            if not generated_kode_batch:
                raise serializers.ValidationError({
                    "batch_code": "Failed to generate kode batch for PDS. Check material, method, sampling area, sampling point, and batch code."
                })

            if qs.filter(kode_batch__iexact=generated_kode_batch).exists():
                material_name = self.get_material_name(attrs) or "-"
                method_name = self.get_method_name(attrs) or "-"
                area_name = self.get_sampling_area_name(attrs) or "-"
                point_name = self.get_sampling_point_name(attrs) or "-"
                batch = attrs.get("batch_code", getattr(self.instance, "batch_code", None)) or "-"

                raise serializers.ValidationError({
                    "batch_code": (
                        f"Duplicate batch: "
                        f"{material_name}, {method_name}, {area_name}, {point_name} (Batch {batch})"
                    )
                })

            attrs["kode_batch"] = generated_kode_batch
        elif str(sample_type or "").upper() == "PSI":
            if not generated_kode_psi:
                raise serializers.ValidationError({
                    "batch_code": "Failed to generate kode PSI. Check material, sampling point, and batch code."
                })

            if qs.filter(kode_batch__iexact=generated_kode_psi).exists():
                material_name = self.get_material_name(attrs) or "-"
                point_name = self.get_sampling_point_name(attrs) or "-"
                batch = attrs.get("batch_code", getattr(self.instance, "batch_code", None)) or "-"

                raise serializers.ValidationError({
                    "batch_code": (
                        f"Duplicate PSI: "
                        f"{material_name}, {point_name} (Batch {batch})"
                    )
                })

            attrs["kode_batch"] = generated_kode_psi
        else:
            attrs["kode_batch"] = None

        # Hapus DUP_
        # isi atau hapus sample_dup otomatis
        attrs["sample_dup"] = self.extract_sample_dup(attrs)
        
        return attrs


    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user

        if not validated_data.get("code"):
            validated_data["code"] = self.build_code(validated_data)

        # return super().create(validated_data)
        instance = super().create(validated_data)

        return instance


    def update(self, instance, validated_data):
        u = self.context["request"].user
        if u.is_site_user:
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)
        return super().update(instance, validated_data)