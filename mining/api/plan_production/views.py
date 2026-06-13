from django.db import connection, transaction
from datetime import timedelta, date
import uuid
import os

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from django.conf import settings

from mining.models import PlanProduction, PlanProductionDetail
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from core.base import BaseViewSet
from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)

from master.api.pagination import StandardResultsSetPagination
from .serializers import planProductionSerializer
from .filters import planFilter

from analytics.models import ExportJob
from analytics.tasks import run_export_job


class planProductionViewSet(BaseViewSet):
    queryset = (
        PlanProduction.objects
        .select_related("iup")
        .prefetch_related("details")
        .all()
        .order_by("-date_plan")
    )
    serializer_class = planProductionSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = planFilter

    search_fields = [
        "date_plan",
        "category",
        "source_code",
        "vendor_code",
        "ref_plan",
        "iup__iup_code",
        "iup__iup_name",
        "details__material_code",
        "details__material_name",
    ]

    ordering_fields = [
        "id",
        "date_plan",
        "category",
        "source_code",
        "vendor_code",
        "ref_plan",
    ]

    soft_delete_field = "is_deleted"
    range_delete_field = "date_plan"
    range_delete_iup_field = "iup_id"

    def _get_iup_id_param(self):
        return self.request.query_params.get("iup_id") or self.request.query_params.get("iup")

    def _get_active_iup_id_for_user(self, user):
        active = getattr(user, "active_iup_id", None) or getattr(user, "iup_id", None)

        if active:
            return str(active)

        allowed = user_allowed_iup_ids(user)

        if not allowed:
            return None

        try:
            return str(next(iter(allowed)))
        except TypeError:
            allowed_list = list(allowed)
            return str(allowed_list[0]) if allowed_list else None

    def _get_request_iup_id(self, request, data):
        iup_id = data.get("iup") or data.get("iup_id")

        if iup_id:
            return iup_id

        user = request.user

        if getattr(user, "is_site_user", False):
            return self._get_active_iup_id_for_user(user)

        return None

    def _normalize_vendor_code(self, data):
        vendor_code = data.get("vendor_code") or data.get("vendors") or None

        if vendor_code is None:
            return None

        vendor_code = str(vendor_code).strip()
        return vendor_code or None

    def _normalize_source_code(self, data):
        source_code = data.get("source_code") or data.get("sources") or None

        if source_code is None:
            return None

        source_code = str(source_code).strip()
        return source_code or None

    def _get_details_payload(self, data):
        details = data.get("details") or data.get("rows") or []

        normalized = []

        for row in details:
            material_code = (
                row.get("material_code")
                or row.get("material")
                or row.get("id_material")
            )
            material_name = (
                row.get("material_name")
                or row.get("material_label")
                or row.get("name")
            )

            tonnage = row.get("tonnage") or row.get("value") or 0

            if not material_code:
                continue

            try:
                tonnage = float(tonnage or 0)
            except (TypeError, ValueError):
                tonnage = 0

            if tonnage <= 0:
                continue

            normalized.append(
                {
                    "material_code": str(material_code),
                    "material_name": str(material_name or material_code),
                    "tonnage": tonnage,
                }
            )

        return normalized

    def _duplicate_queryset(self, iup_id, current_date, category, source_code, vendor_code):
        qs = PlanProduction.objects.filter(
            iup_id=iup_id,
            date_plan=current_date,
            category=category,
        )

        if source_code:
            qs = qs.filter(source_code=source_code)
        else:
            qs = qs.filter(source_code__isnull=True) | qs.filter(source_code="")

        if vendor_code:
            qs = qs.filter(vendor_code=vendor_code)
        else:
            qs = qs.filter(vendor_code__isnull=True) | qs.filter(vendor_code="")

        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        iup_id = self._get_iup_id_param()

        if (
            getattr(user, "is_system", False)
            or getattr(user, "is_superuser", False)
            or getattr(user, "role", None) == "SYSTEM"
        ):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)

            if not iup_id:
                return qs.none()

            return qs.filter(iup_id=iup_id)

        allowed = user_allowed_iup_ids(user)

        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        date_start = data.get("date_start")
        date_end = data.get("date_end")

        if not date_start or not date_end:
            return Response(
                {"date_start": ["Period start and end wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = date.fromisoformat(date_start)
            end = date.fromisoformat(date_end)
        except ValueError:
            return Response(
                {"date_start": ["Format tanggal tidak valid. Gunakan YYYY-MM-DD."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if end < start:
            return Response(
                {"date_end": ["Tanggal akhir tidak boleh lebih kecil dari tanggal awal."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        days_count = (end - start).days + 1

        if days_count > 31:
            return Response(
                {"date_end": ["Periode maksimal 1 bulan."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        iup_id = self._get_request_iup_id(request, data)
        category = data.get("category") or "Mining"
        source_code = self._normalize_source_code(data)
        vendor_code = self._normalize_vendor_code(data)
        ref_plan = data.get("ref_plan") or None

        if not iup_id:
            return Response(
                {"iup": ["IUP wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        details = self._get_details_payload(data)

        if not details:
            return Response(
                {"details": ["Minimal satu material dengan tonnage wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicates = []
        check_date = start

        while check_date <= end:
            if self._duplicate_queryset(
                iup_id,
                check_date,
                category,
                source_code,
                vendor_code,
            ).exists():
                duplicates.append(check_date.isoformat())

            check_date += timedelta(days=1)

        if duplicates:
            return Response(
                {
                    "detail": "Plan Production sudah ada pada beberapa tanggal.",
                    "duplicates": duplicates,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        current = start

        with transaction.atomic():
            while current <= end:
                code = f"PP-{current.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

                plan = PlanProduction.objects.create(
                    code=code,
                    iup_id=iup_id,
                    date_plan=current,
                    category=category,
                    source_code=source_code,
                    vendor_code=vendor_code,
                    ref_plan=ref_plan,
                    user=request.user if request.user.is_authenticated else None,
                )

                detail_objects = []

                for item in details:
                    daily_tonnage = item["tonnage"] / days_count

                    detail_objects.append(
                        PlanProductionDetail(
                            plan=plan,
                            material_code=item["material_code"],
                            material_name=item["material_name"],
                            tonnage=daily_tonnage,
                        )
                    )

                PlanProductionDetail.objects.bulk_create(detail_objects)

                created.append(plan)
                current += timedelta(days=1)

        serializer = self.get_serializer(created, many=True)

        return Response(
            {
                "count": len(created),
                "results": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="mining.plan_productions",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "import queued", "job_id": str(job.id)},
            status=202,
        )

    def handle_export(self, request):
        params = {}

        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="mining.plan_productions",
            params=params,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_export_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "export queued", "job_id": str(job.id)},
            status=202,
        )

    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "mining_plan_productions_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="mining_plan_productions_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )