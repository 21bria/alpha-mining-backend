from rest_framework import serializers
import json
from datetime import date
from calendar import monthrange

from analytics.models_report_management import (
    ReportManagement,
    ReportManagementMining,
    ReportManagementMetric,
    ReportManagementManpower,
    ReportManagementDocument,
    ReportManagementTarget,   # baru
)

class ReportManagementMiningSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportManagementMining
        fields = [
            "id",
            "material",
            "plan",
            "actual",
            "achievement",
            "status",
            "group",
            "is_total",
            "is_grand_total",
            "source_module",
            "sort_order",
        ]


class ReportManagementMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportManagementMetric
        fields = [
            "id",
            "code",          # baru
            "section",
            "title",
            "value",
            "suffix",
            "description",
            "source_module",
            "sort_order",
        ]

    def validate_code(self, value):
        return str(value or "").strip().upper()

class ReportManagementTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportManagementTarget
        fields = [
            "id",
            "code",
            "title",
            "plan",
            "unit",
        ]

    def validate_code(self, value):
        return str(value or "").strip().upper()
    
class ReportManagementManpowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportManagementManpower
        fields = [
            "id",
            "contractor",
            "personnel",
            "description",
            "source_module",
            "sort_order",
        ]


class ReportManagementDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportManagementDocument
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
            "report": {"required": False},
            "title": {"required": False, "allow_blank": True, "allow_null": True},
            "document_date": {"required": False, "allow_null": True},
            "file_name": {"required": False, "allow_blank": True, "allow_null": True},
            "document_type": {"required": False, "allow_blank": True, "allow_null": True},
            "external_url": {"required": False, "allow_blank": True, "allow_null": True},
            "description": {"required": False, "allow_blank": True, "allow_null": True},
        }

    def get_file_url(self, obj):
        request = self.context.get("request")

        if not obj.file:
            return None

        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

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


class ReportManagementSerializer(serializers.ModelSerializer):
    iup_code = serializers.CharField(source="iup.iup_code", read_only=True)
    iup_name = serializers.CharField(source="iup.iup_name", read_only=True)

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    mining_rows = ReportManagementMiningSerializer(many=True, required=False)
    metrics = ReportManagementMetricSerializer(many=True, required=False)
    targets = ReportManagementTargetSerializer(many=True, required=False)
    manpower_rows = ReportManagementManpowerSerializer(many=True, required=False)
    documents = ReportManagementDocumentSerializer(many=True, required=False)

    class Meta:
        model = ReportManagement
        fields = [
            "id",
            "iup",
            "iup_code",
            "iup_name",
            "report_code",
            "title",
            "period_type",
            "period_key",
            "year",
            "month",
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
            "targets", 
            "manpower_rows",
            "documents",
            "hse_incidents",
            "total_movement",
            "total_production",
            "total_barging",
            "total_inventory",
            "avg_ni",
            "stockpile_count",
            "last_synced_at",
            "published_at",
            "published_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "report_code",
            "period_key",
            "user",
            "user_id",
            "username",
            "created_at",
            "updated_at",
        ]

    def calc_achievement(self, plan, actual):
        plan = float(plan or 0)
        actual = float(actual or 0)

        if plan <= 0:
            return 0

        return round((actual / plan) * 100, 2)

    def build_period_key(self, period_type, year=None, month=None, week=None, period_start=None, period_end=None):
        if period_type == "weekly":
            return f"{year}-W{str(week).zfill(2)}"

        if period_type == "monthly":
            return f"{year}-{str(month).zfill(2)}"

        if period_type == "yearly":
            return str(year)

        if period_type == "range":
            return f"{period_start}_{period_end}"

        return None

    def build_code(self, iup, period_type, year=None, month=None, week=None, period_start=None, period_end=None):
        iup_code = getattr(iup, "iup_code", "NO-IUP")

        if period_type == "weekly":
            return f"{iup_code}-W{str(week).zfill(2)}-{year}"

        if period_type == "monthly":
            return f"{iup_code}-M{str(month).zfill(2)}-{year}"

        if period_type == "yearly":
            return f"{iup_code}-Y{year}"

        if period_type == "range":
            return f"{iup_code}-range-{period_start}-{period_end}"

        return f"{iup_code}-REPORT"

    def normalize_period_dates(self, attrs):
        period_type = attrs.get("period_type")
        year = attrs.get("year")
        month = attrs.get("month")
        week = attrs.get("week")
        period_start = attrs.get("period_start")
        period_end = attrs.get("period_end")

        if period_type == "monthly" and year and month:
            attrs["period_start"] = date(year, month, 1)
            attrs["period_end"] = date(year, month, monthrange(year, month)[1])

        elif period_type == "yearly" and year:
            attrs["period_start"] = date(year, 1, 1)
            attrs["period_end"] = date(year, 12, 31)

        elif period_type == "weekly":
            if not period_start or not period_end:
                raise serializers.ValidationError({
                    "period_start": "period_start dan period_end wajib untuk weekly."
                })

        elif period_type == "range":
            if not period_start or not period_end:
                raise serializers.ValidationError({
                    "period_start": "period_start dan period_end wajib untuk range."
                })

        return attrs

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
                row.get("plan"),
                row.get("actual"),
            )
            result.append(row)

        production_plan = sum(float(row.get("plan") or 0) for row in production_rows)
        production_actual = sum(float(row.get("actual") or 0) for row in production_rows)

        if production_rows:
            result.append({
                "material": "SUB-TOTAL",
                "plan": production_plan,
                "actual": production_actual,
                "achievement": self.calc_achievement(production_plan, production_actual),
                "status": "UP" if production_actual >= production_plan else "DOWN",
                "group": "TOTAL",
                "is_total": True,
                "is_grand_total": False,
                "source_module": "AUTO",
                "sort_order": 900,
            })

        total_plan = production_plan + sum(float(row.get("plan") or 0) for row in barging_rows)
        total_actual = production_actual + sum(float(row.get("actual") or 0) for row in barging_rows)

        if detail_rows:
            result.append({
                "material": "TOTAL",
                "plan": total_plan,
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

        for key in ["mining_rows", "metrics","targets", "manpower_rows", "documents"]:
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
        period_type = attrs.get("period_type", getattr(self.instance, "period_type", None))
        year = attrs.get("year", getattr(self.instance, "year", None))
        month = attrs.get("month", getattr(self.instance, "month", None))
        week = attrs.get("week", getattr(self.instance, "week", None))
        period_start = attrs.get("period_start", getattr(self.instance, "period_start", None))
        period_end = attrs.get("period_end", getattr(self.instance, "period_end", None))

        if not iup:
            raise serializers.ValidationError({"iup": "IUP is required."})

        if not period_type:
            raise serializers.ValidationError({"period_type": "Period type is required."})

        if period_type in ["weekly", "monthly", "yearly"] and not year:
            raise serializers.ValidationError({"year": "Year is required."})

        if period_type == "weekly" and not week:
            raise serializers.ValidationError({"week": "Week is required for weekly report."})

        if period_type == "monthly" and not month:
            raise serializers.ValidationError({"month": "Month is required for monthly report."})

        attrs = self.normalize_period_dates(attrs)

        period_start = attrs.get("period_start", period_start)
        period_end = attrs.get("period_end", period_end)

        if period_start and period_end and period_start > period_end:
            raise serializers.ValidationError({
                "period_end": "period_end tidak boleh lebih kecil dari period_start."
            })

        period_key = self.build_period_key(
            period_type=period_type,
            year=year,
            month=month,
            week=week,
            period_start=period_start,
            period_end=period_end,
        )

        if not period_key:
            raise serializers.ValidationError({
                "period_key": "Period key tidak valid."
            })

        attrs["period_key"] = period_key

        qs = ReportManagement.objects.filter(
            iup=iup,
            period_type=period_type,
            period_key=period_key,
            is_deleted=False,
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Report management untuk IUP ini, periode {period_key} sudah ada."
                ]
            })
        
        title = str(attrs.get("title") or "").strip()

        if title and not attrs.get("code"):
            attrs["code"] = (
                title.upper()
                    .replace(" ", "_")
                    .replace("-", "_")
            )

        return attrs

    def _save_children(self, instance, child_data):
        mining_rows = child_data.get("mining_rows")
        metrics = child_data.get("metrics")
        targets = child_data.get("targets")
        manpower_rows = child_data.get("manpower_rows")
        documents = child_data.get("documents")

        if mining_rows is not None:
            instance.mining_rows.all().delete()

            mining_rows = self.normalize_mining_rows(mining_rows)

            ReportManagementMining.objects.bulk_create([
                ReportManagementMining(report=instance, **row)
                for row in mining_rows
            ])

        if metrics is not None:
            print("========== METRICS ==========")
            for row in metrics:
                print(row)
            instance.metrics.all().delete()
            ReportManagementMetric.objects.bulk_create([
                ReportManagementMetric(report=instance, **row)
                for row in metrics
            ])

        if targets is not None:
            instance.targets.all().delete()
            ReportManagementTarget.objects.bulk_create([
                ReportManagementTarget(
                    report=instance,
                    **row,
                )
                for row in targets
            ])

        if manpower_rows is not None:
            instance.manpower_rows.all().delete()

            ReportManagementManpower.objects.bulk_create([
                ReportManagementManpower(report=instance, **row)
                for row in manpower_rows
            ])

        if documents is not None:
            instance.documents.all().delete()

            for row in documents:
                ReportManagementDocument.objects.create(
                    report=instance,
                    **row,
                )

    def create(self, validated_data):
        request = self.context.get("request")

        child_data = {
            "mining_rows": validated_data.pop("mining_rows", None),
            "metrics": validated_data.pop("metrics", None),
             "targets": validated_data.pop("targets", None),
            "manpower_rows": validated_data.pop("manpower_rows", None),
            "documents": validated_data.pop("documents", None),
        }

        report_code = self.build_code(
            iup=validated_data["iup"],
            period_type=validated_data["period_type"],
            year=validated_data.get("year"),
            month=validated_data.get("month"),
            week=validated_data.get("week"),
            period_start=validated_data.get("period_start"),
            period_end=validated_data.get("period_end"),
        )

        validated_data["report_code"] = report_code
        validated_data["code"] = report_code

        if request and request.user and request.user.is_authenticated:
            validated_data["user"] = request.user

        instance = ReportManagement.objects.create(**validated_data)

        self._save_children(instance, child_data)

        return instance

    def update(self, instance, validated_data):
        child_data = {
            "mining_rows": validated_data.pop("mining_rows", None),
            "metrics": validated_data.pop("metrics", None),
            "targets": validated_data.pop("targets", None),
            "manpower_rows": validated_data.pop("manpower_rows", None),
            "documents": validated_data.pop("documents", None),
        }

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.report_code = self.build_code(
            iup=instance.iup,
            period_type=instance.period_type,
            year=instance.year,
            month=instance.month,
            week=instance.week,
            period_start=instance.period_start,
            period_end=instance.period_end,
        )
        instance.code = instance.report_code

        instance.save()

        self._save_children(instance, child_data)

        return instance