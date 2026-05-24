from rest_framework import serializers
import json
from analytics.models_bod_weekly import (
    BodWeeklyReport,
    BodWeeklyMining,
    BodWeeklyMetric,
    BodWeeklyManpower,
    BodWeeklyDocument,
)

class BodWeeklyMiningSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodWeeklyMining
        fields = [
            "id",
            "material",
            "weekly_plan",
            "actual",
            "achievement",
            "status",
            "group",
            "is_total",
            "is_grand_total",
            "source_module",
            "sort_order",
        ]
        
   

class BodWeeklyMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodWeeklyMetric
        fields = [
            "id",
            "section",
            "title",
            "value",
            "suffix",
            "description",
            "source_module",
            "sort_order",
        ]


class BodWeeklyManpowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodWeeklyManpower
        fields = [
            "id",
            "contractor",
            "personnel",
            "description",
            "source_module",
            "sort_order",
        ]

class BodWeeklyDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = BodWeeklyDocument
        fields = [
            "id",
            "report",
            "title",
            "document_date",
            "file_name",
            "document_type",
            "file",
            "file_url",
            "external_url",
            "description",
            "sort_order",
        ]

        extra_kwargs = {
            "title": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "document_date": {
                "required": False,
                "allow_null": True,
            },
            "file_name": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "document_type": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "external_url": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "description": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
        }

    def get_file_url(self, obj):
        request = self.context.get("request")

        if not obj.file:
            return None

        url = obj.file.url

        return (
            request.build_absolute_uri(url)
            if request else url
        )

    def validate(self, attrs):
        file = attrs.get("file")
        external_url = attrs.get("external_url")

        if file:
            attrs["file_name"] = file.name

            ext = file.name.split(".")[-1].lower()

            if ext == "pdf":
                attrs["document_type"] = "PDF"
            elif ext in ["xls", "xlsx"]:
                attrs["document_type"] = "EXCEL"
            elif ext in ["png", "jpg", "jpeg", "webp"]:
                attrs["document_type"] = "IMAGE"
            else:
                attrs["document_type"] = "OTHER"

        elif external_url:
            attrs["document_type"] = "LINK"

        return attrs


class BodWeeklyReportSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    mining_rows = BodWeeklyMiningSerializer(many=True, required=False)
    metrics = BodWeeklyMetricSerializer(many=True, required=False)
    manpower_rows = BodWeeklyManpowerSerializer(many=True, required=False)
    documents = BodWeeklyDocumentSerializer(many=True, required=False)

    class Meta:
        model = BodWeeklyReport
        fields = [
            "id",
            "iup",
            "iup_code",
            "iup_name",
            "report_code",
            "title",
            "year",
            "week",
            "period_start",
            "period_end",
            "status",
            "summary_cards",
            "notes",
            "remarks",
            "user",
            "user_id",
            "username",
            "mining_rows",
            "metrics",
            "manpower_rows",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "report_code",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def build_code(self, iup, year, week):
        iup_code = getattr(iup, "iup_code", "NO-IUP")
        return f"{iup_code}-W{week}-{year}"
    
    def calc_achievement(self, plan, actual):
        plan = float(plan or 0)
        actual = float(actual or 0)

        if plan <= 0:
            return 0

        return round((actual / plan) * 100, 2)


    def normalize_mining_rows(self, rows):
        rows = rows or []

        detail_rows = [
            row for row in rows
            if not row.get("is_total") and not row.get("is_grand_total")
        ]

        production_rows = [
            row for row in detail_rows
            if row.get("group") in ["ORE", "WASTE"]
        ]

        barging_rows = [
            row for row in detail_rows
            if row.get("group") == "BARGING"
        ]

        result = []

        for idx, row in enumerate(detail_rows, start=1):
            row["sort_order"] = row.get("sort_order") or idx
            row["achievement"] = self.calc_achievement(
                row.get("weekly_plan"),
                row.get("actual"),
            )
            result.append(row)

        production_plan = sum(float(row.get("weekly_plan") or 0) for row in production_rows)
        production_actual = sum(float(row.get("actual") or 0) for row in production_rows)

        if production_rows:
            result.append({
                "material": "SUB-TOTAL",
                "weekly_plan": production_plan,
                "actual": production_actual,
                "achievement": self.calc_achievement(production_plan, production_actual),
                "status": "UP" if production_actual >= production_plan else "DOWN",
                "group": "TOTAL",
                "is_total": True,
                "is_grand_total": False,
                "source_module": "AUTO",
                "sort_order": 900,
            })

        total_plan = production_plan + sum(float(row.get("weekly_plan") or 0) for row in barging_rows)
        total_actual = production_actual + sum(float(row.get("actual") or 0) for row in barging_rows)

        if detail_rows:
            result.append({
                "material": "TOTAL",
                "weekly_plan": total_plan,
                "actual": total_actual,
                "achievement": self.calc_achievement(total_plan, total_actual),
                "status": "UP" if total_actual >= total_plan else "DOWN",
                "group": "TOTAL",
                "is_total": True,
                "is_grand_total": True,
                "source_module": "AUTO",
                "sort_order": 999,
            })

        return result
    
    def to_internal_value(self, data):
        data = data.copy()

        for key in ["mining_rows", "metrics", "manpower_rows", "documents"]:
            value = data.get(key)

            if isinstance(value, str):
                data[key] = json.loads(value) if value else []

        request = self.context.get("request")

        if request:
            documents = data.get("documents") or []

            for doc in documents:
                file_key = doc.pop("file_key", None)

                if file_key and file_key in request.FILES:
                    doc["file"] = request.FILES[file_key]

        return super().to_internal_value(data)
    
    def validate(self, attrs):
        iup = attrs.get("iup", getattr(self.instance, "iup", None))
        year = attrs.get("year", getattr(self.instance, "year", None))
        week = attrs.get("week", getattr(self.instance, "week", None))

        if not iup:
            raise serializers.ValidationError({"iup": "IUP is required."})

        if not year:
            raise serializers.ValidationError({"year": "Year is required."})

        if not week:
            raise serializers.ValidationError({"week": "Week is required."})

        qs = BodWeeklyReport.objects.filter(
            iup=iup,
            year=year,
            week=week,
            is_deleted=False,
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"BOD weekly report untuk IUP ini, year {year}, week {week} sudah ada."
                ]
            })

        return attrs

    def _save_children(self, instance, child_data):
        mining_rows = child_data.get("mining_rows")
        metrics = child_data.get("metrics")
        manpower_rows = child_data.get("manpower_rows")
        documents = child_data.get("documents")

        if mining_rows is not None:
            instance.mining_rows.all().delete()

            mining_rows = self.normalize_mining_rows(mining_rows)

            BodWeeklyMining.objects.bulk_create([
                BodWeeklyMining(
                    report=instance,
                    **row,
                )
                for row in mining_rows
            ])

        if metrics is not None:
            instance.metrics.all().delete()

            BodWeeklyMetric.objects.bulk_create([
                BodWeeklyMetric(
                    report=instance,
                    **row,
                )
                for row in metrics
            ])

        if manpower_rows is not None:
            instance.manpower_rows.all().delete()

            BodWeeklyManpower.objects.bulk_create([
                BodWeeklyManpower(
                    report=instance,
                    **row,
                )
                for row in manpower_rows
            ])

        if documents is not None:
            instance.documents.all().delete()

            for row in documents:
                BodWeeklyDocument.objects.create(
                    report=instance,
                    **row,
                )

    def create(self, validated_data):
        request = self.context.get("request")

        child_data = {
            "mining_rows": validated_data.pop("mining_rows", None),
            "metrics": validated_data.pop("metrics", None),
            "manpower_rows": validated_data.pop("manpower_rows", None),
            "documents": validated_data.pop("documents", None),
        }

        report_code = self.build_code(
            validated_data["iup"],
            validated_data["year"],
            validated_data["week"],
        )

        validated_data["report_code"] = report_code
        validated_data["code"] = report_code

        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        instance = BodWeeklyReport.objects.create(**validated_data)

        self._save_children(instance, child_data)

        return instance

    def update(self, instance, validated_data):
        child_data = {
            "mining_rows": validated_data.pop("mining_rows", None),
            "metrics": validated_data.pop("metrics", None),
            "manpower_rows": validated_data.pop("manpower_rows", None),
            "documents": validated_data.pop("documents", None),
        }

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.report_code = self.build_code(
            instance.iup,
            instance.year,
            instance.week,
        )
        instance.code = instance.report_code

        instance.save()

        self._save_children(instance, child_data)

        return instance