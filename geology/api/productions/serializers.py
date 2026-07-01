from django.utils import timezone
import random
from rest_framework import serializers
from django.db.models import Sum
from geology.models import OreProductions,OreProductionsView,ProductionsConfig
from master.models import SourceMinesLoading,SourceMinesDumping,SourceMinesDome,Material,Block,SourcePitDome,SampleType
from master.services.sample_type import (
    get_production_geology_sample_type_map,
    build_pattern,
)

class ProductionsSerializer(serializers.ModelSerializer):
    tonnage = serializers.SerializerMethodField()

    class Meta:
        model = OreProductionsView
        fields = [
            "id",
            "iup_id", "iup_code", "iup_name",
            "category",
            "tgl_production",
            "shift",

            "prospect_area",
            "mine_block",
            "from_rl",
            "to_rl",

            "nama_material",
            "ore_class",
            "ni_grade",
            "grade_control",
            "unit_truck",
            "stockpile",
            "pile_id",
            "batch_code",
            "increment",
            "batch_status",
            "ritase",
            "tonnage",
            "pile_status",
            "truck_factor",
            "remarks",
            "sample_number",
            "no_production",
            "sample_type",
            "direct",
            "created_at",
            "user_id",
            "username"
        ]
        
    def _fmt_decimal(self, value):
        if value is None:
            return "-"
        return f"{float(value):.2f}"

    def get_tonnage(self, obj):
        return self._fmt_decimal(obj.tonnage)

class ProductionsCRUDSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)


    prospect_label = serializers.SerializerMethodField()
    pit_dome_label = serializers.SerializerMethodField()
    block_label = serializers.SerializerMethodField()
    material_label = serializers.SerializerMethodField()
    stockpile_label = serializers.SerializerMethodField()
    pile_label = serializers.SerializerMethodField()
    sample_type_label = serializers.SerializerMethodField()

    class Meta:
        model = OreProductions
        fields = [
            "id",
            "iup", "iup_code", "iup_name",
            "tgl_production",
            "shift",

            "id_block", "block_label",
            "id_prospect_area", "prospect_label",
            "id_pit_dome", "pit_dome_label",

            "from_rl",
            "to_rl",
            "id_material", "material_label",
            "grade_expect",
            "grade_control",
            "unit_truck",
            "id_stockpile", "stockpile_label",
            "id_pile", "pile_label",
            "batch_code",
            "increment",
            "batch_status",
            "ritase",
            "tonnage",
            "pile_status",
            "kode_batch",
            "pile_original",
            "stockpile_ori",
            "truck_factor",
            "ore_class",
            "batch_status_set",
            "dome_compositing",
            "stock_compositing",
            "status_dome",
            "sale_adjust",
            "remarks",
            "category",
            "direct",
            "no_production",
            "sample_type", "sample_type_label",
            "user",
        ]
        read_only_fields = [
            "kode_batch",
            "id_stockpile",
            "user",
        ]

    def build_code(self, validated_data):
        iup = validated_data.get("iup")
        iup_code = getattr(iup, "iup_code", f"IUP-{iup.id}")

        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        suffix = random.randint(1000, 9999)

        return f"{iup_code}-{ts}-{suffix}"
    
    def get_prospect_label(self, obj):
        if not obj.id_prospect_area:
            return None
        row = SourceMinesLoading.objects.filter(id=obj.id_prospect_area).only("loading_point").first()
        return row.loading_point if row else None
    
    def get_pit_dome_label(self, obj):
        if not obj.id_pit_dome:
            return None

        row = SourcePitDome.objects.filter(id=obj.id_pit_dome).only("dome").first()
        return row.dome if row else None

    def get_block_label(self, obj):
        if not obj.id_block:
            return None
        row = Block.objects.filter(id=obj.id_block).only("name").first()
        return row.name if row else None

    def get_material_label(self, obj):
        if not obj.id_material:
            return None
        row = Material.objects.filter(id=obj.id_material).only("name").first()
        return row.name if row else None

    def get_stockpile_label(self, obj):
        if not obj.id_stockpile:
            return None
        row = SourceMinesDumping.objects.filter(id=obj.id_stockpile).only("dumping_point").first()
        return row.dumping_point if row else None

    def get_pile_label(self, obj):
        if not obj.id_pile:
            return None
        row = SourceMinesDome.objects.filter(id=obj.id_pile).only("pile_id").first()
        return row.pile_id if row else None
    
    def get_sample_type_label(self, obj):
        if not obj.sample_type:
            return None

        row = SampleType.objects.filter(id=obj.sample_type).only("type_sample").first()
        return row.type_sample if row else None
    
    def get_pit_dome_name(self, attrs):
        pit_dome_id = attrs.get("id_pit_dome", getattr(self.instance, "id_pit_dome", None))

        if not pit_dome_id:
            return None

        row = SourcePitDome.objects.filter(id=pit_dome_id).only("dome").first()
        return row.dome if row else None
    
    def get_sample_type_name(self, attrs):
        sample_type = attrs.get("sample_type",getattr(self.instance, "sample_type", None))

        if not sample_type:
            return None
        
        row = SampleType.objects.filter(id=sample_type).only("type_sample").first()
        return row.type_sample if row else None

    def get_material_name(self, attrs):
        material_id = attrs.get("id_material", getattr(self.instance, "id_material", None))
        if not material_id:
            return None
        row = Material.objects.filter(id=material_id).only("name").first()
        return row.name if row else None

    def get_stockpile_name(self, attrs):
        stockpile_id = attrs.get("id_stockpile", getattr(self.instance, "id_stockpile", None))
        if not stockpile_id:
            return None
        row = SourceMinesDumping.objects.filter(id=stockpile_id).only("dumping_point").first()
        return row.dumping_point if row else None

    def get_pile_name(self, attrs):
        pile_id = attrs.get("id_pile", getattr(self.instance, "id_pile", None))
        if not pile_id:
            return None
        row = SourceMinesDome.objects.filter(id=pile_id).only("pile_id").first()
        return row.pile_id if row else None

    def resolve_stockpile_from_pile(self, attrs):
        pile_id = attrs.get("id_pile", getattr(self.instance, "id_pile", None))
        if not pile_id:
            return None

        pile = SourceMinesDome.objects.filter(id=pile_id).only("dumping").first()
        return pile.dumping_id if pile and pile.dumping_id else None
    
    def resolve_original_ids(self, attrs):
        pile_id = attrs.get(
            "id_pile",
            getattr(self.instance, "id_pile", None),
        )

        stockpile_id = attrs.get(
            "id_stockpile",
            getattr(self.instance, "id_stockpile", None),
        )

        return {
            "pile_original": pile_id,
            "stockpile_ori": stockpile_id,
        }
    
    def resolve_sale_adjust(self, attrs):
        material_id = attrs.get("id_material", getattr(self.instance, "id_material", None))

        if not material_id:
            return None

        material = Material.objects.filter(id=material_id).only("sale_adjust").first()
        return material.sale_adjust if material else None
    
    def build_kode_batch(self, attrs):
        material_id = attrs.get("id_material", getattr(self.instance, "id_material", None))
        unit_truck = attrs.get("unit_truck", getattr(self.instance, "unit_truck", None))
        pile_id = attrs.get("id_pile", getattr(self.instance, "id_pile", None))
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))
        sample_type_id = attrs.get("sample_type", getattr(self.instance, "sample_type", None))

        if not material_id or not sample_type_id:
            return None

        sample = (
            SampleType.objects
            .filter(id=sample_type_id)
            .only("type_sample")
            .first()
        )

        if not sample:
            return None

        sample_type_name = sample.type_sample.upper()

        sample_type_map = get_production_geology_sample_type_map()
        cfg = sample_type_map.get(sample_type_name)

        if not cfg:
            return None

        pit_dome = self.get_pit_dome_name(attrs)

        if sample_type_name == "PDS_QA":
            if not unit_truck or not pile_id or not batch_code:
                return None

        elif sample_type_name == "PDS_GC":
            if not pit_dome:
                return None

        return build_pattern(
            cfg.get("batch_pattern"),
            type=sample_type_name,
            material=str(material_id),
            truck=unit_truck or "",
            point=str(pile_id or ""),
            pit_dome=pit_dome or "",
            batch=batch_code or "",
        )
    
    def update_batch_status(self, instance):
        batch_status = getattr(instance, "batch_status", None)
        batch_code = getattr(instance, "batch_code", None)
        id_pile = getattr(instance, "id_pile", None)

        if not batch_status or not batch_code or not id_pile:
            return

        if batch_status.strip() == "Complete":
            OreProductions.objects.filter(
                id_pile=id_pile,
                batch_code=batch_code,
                is_deleted=False
            ).exclude(id=instance.id).update(batch_status="Complete")


    def validate(self, attrs):
        iup = attrs.get("iup", getattr(self.instance, "iup", None))
        if not iup:
            raise serializers.ValidationError({
                "iup": "IUP is required."
            })
        
        prospect_id = attrs.get(
            "id_prospect_area",
            getattr(self.instance, "id_prospect_area", None)
        )

        pit_dome_id = attrs.get(
            "id_pit_dome",
            getattr(self.instance, "id_pit_dome", None)
        )

        if prospect_id:
            if not pit_dome_id:
                default_dome = SourcePitDome.objects.filter(
                    loading_point_id=prospect_id,
                    dome__iexact="ALL",
                    is_active=True,
                ).first()

                if default_dome:
                    attrs["id_pit_dome"] = default_dome.id

            else:
                pit_dome = SourcePitDome.objects.filter(id=pit_dome_id).first()

                if not pit_dome:
                    raise serializers.ValidationError({
                        "id_pit_dome": "Pit dome tidak ditemukan."
                    })

                if pit_dome.loading_point_id != prospect_id:
                    raise serializers.ValidationError({
                        "id_pit_dome": "Pit dome tidak sesuai dengan loading point/prospect area."
                    })

        # auto isi id_stockpile dari pile
        stockpile_id = self.resolve_stockpile_from_pile(attrs)
        if not stockpile_id:
            raise serializers.ValidationError({
                "id_pile": "Selected dome/pile has no related stockpile."
            })

        attrs["id_stockpile"] = stockpile_id

        originals = self.resolve_original_ids(attrs)

        attrs["pile_original"] = originals["pile_original"]
        attrs["stockpile_ori"] = originals["stockpile_ori"]
        
        # DEFAULT STATUS
        if not attrs.get("pile_status"):
            attrs["pile_status"] = "Continue"

        if not attrs.get("status_dome"):
            attrs["status_dome"] = "Continue"

        if not attrs.get("sale_adjust"):
            sale_adjust = self.resolve_sale_adjust(attrs)
            if sale_adjust:
                attrs["sale_adjust"] = sale_adjust   

        qs = OreProductions.objects.filter(
            iup=iup,
            is_deleted=False
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        generated_kode_batch = self.build_kode_batch(attrs)

        if not generated_kode_batch:
            raise serializers.ValidationError({
                "batch_code": "Failed to generate kode batch. Check material, unit truck, dome/pile, and batch code."
            })
        
        attrs["kode_batch"] = generated_kode_batch
 
       # GET CONFIG MAX INCREMENT
        max_increment = ProductionsConfig.objects.filter(
            key="MAX_INCREMENT_PRODUCTION"
        ).values_list("value", flat=True).first() or 10

        # CHECK INCREMENT
        material_id = attrs.get("id_material",getattr(self.instance, "id_material", None))

        unit_truck = attrs.get( "unit_truck",getattr(self.instance, "unit_truck", None))

        pile_id = attrs.get("id_pile",getattr(self.instance, "id_pile", None) )

        batch_code = attrs.get("batch_code",getattr(self.instance, "batch_code", None) )

        current_increment = attrs.get("increment",
            getattr(self.instance, "increment", 0)
        ) or 0

        increment_qs = qs.filter(
            id_material=material_id,
            unit_truck=unit_truck,
            id_pile=pile_id,
            batch_code=batch_code,
        )

        existing_total = increment_qs.aggregate(
            total=Sum("increment")
        )["total"] or 0

        if existing_total + current_increment > max_increment:
            raise serializers.ValidationError({
                "increment": (
                    f"Total increment maksimal {max_increment} "
                    # "untuk kombinasi batch yang sama."
                )
            })
        
        return attrs
    

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user

        if not validated_data.get("code"):
            validated_data["code"] = self.build_code(validated_data)

        instance = super().create(validated_data)
        self.update_batch_status(instance)

        return instance

    def update(self, instance, validated_data):
        u = self.context["request"].user

        if getattr(u, "is_site_user", False):
            validated_data.pop("iup", None)
            validated_data.pop("iup_id", None)

        instance = super().update(instance, validated_data)

        # update batch jika complete
        self.update_batch_status(instance)

        return instance