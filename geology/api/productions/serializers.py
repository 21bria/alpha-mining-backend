from rest_framework import serializers
import re
from geology.models import OreProductions,OreProductionsView
from master.models import SourceMinesLoading,SourceMinesDumping,SourceMinesDome,Material,Block

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
    block_label = serializers.SerializerMethodField()
    material_label = serializers.SerializerMethodField()
    stockpile_label = serializers.SerializerMethodField()
    pile_label = serializers.SerializerMethodField()

    class Meta:
        model = OreProductions
        fields = [
            "id",
            "iup", "iup_code", "iup_name",
            "tgl_production",
            "shift",

            "id_block", "block_label",
            "id_prospect_area", "prospect_label",

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
            "user",
        ]
        read_only_fields = [
            "kode_batch",
            "id_stockpile",
            "user",
        ]

    def get_prospect_label(self, obj):
        if not obj.id_prospect_area:
            return None
        row = SourceMinesLoading.objects.filter(id=obj.id_prospect_area).only("loading_point").first()
        return row.loading_point if row else None

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


    def build_kode_batch(self, attrs):
        material_id = attrs.get("id_material", getattr(self.instance, "id_material", None))
        unit_truck = attrs.get("unit_truck", getattr(self.instance, "unit_truck", None))
        stockpile_id = attrs.get("id_stockpile", getattr(self.instance, "id_stockpile", None))
        pile_id = attrs.get("id_pile", getattr(self.instance, "id_pile", None))
        batch_code = attrs.get("batch_code", getattr(self.instance, "batch_code", None))

        if not material_id or not unit_truck or not stockpile_id or not pile_id or not batch_code:
            return None

        return f"PDS{material_id}{unit_truck}{stockpile_id}{pile_id}{batch_code}"
    
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

        # auto isi id_stockpile dari pile
        stockpile_id = self.resolve_stockpile_from_pile(attrs)
        if not stockpile_id:
            raise serializers.ValidationError({
                "id_pile": "Selected dome/pile has no related stockpile."
            })

        attrs["id_stockpile"] = stockpile_id
        # DEFAULT STATUS
        if not attrs.get("pile_status"):
            attrs["pile_status"] = "Continue"

        if not attrs.get("status_dome"):
            attrs["status_dome"] = "Continue"

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

        # if qs.filter(kode_batch__iexact=generated_kode_batch).exists():
        #     material_name = self.get_material_name(attrs) or "-"
        #     stockpile_name = self.get_stockpile_name(attrs) or "-"
        #     pile_name = self.get_pile_name(attrs) or "-"
        #     batch = attrs.get("batch_code", getattr(self.instance, "batch_code", None)) or "-"

        #     raise serializers.ValidationError({
        #         "batch_code": (
        #             f"Duplicate batch: "
        #             f"{material_name}, {stockpile_name}, {pile_name} (Batch {batch})"
        #         )
        #     })

        attrs["kode_batch"] = generated_kode_batch
        return attrs
    

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        instance = super().create(validated_data)

        # update batch jika complete
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