from django.db import connection
from datetime import timedelta, date
import uuid

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from mining.models import planBarging

from core.base import BaseViewSet
from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)

from master.api.pagination import StandardResultsSetPagination
from .serializers import planBargingSerializer
from .filters import planFilter

from analytics.models import ExportJob
from analytics.tasks import run_export_job


class planBargingViewSet(BaseViewSet):
    queryset = planBarging.objects.select_related("iup").all().order_by("-date_plan")
    serializer_class = planBargingSerializer
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
        "vendor_code",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "date_plan",
        "category",
        "vendor_code",
        "lim",
        "sap",
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

    def _duplicate_queryset(self, iup_id, current_date, category, vendor_code):
        qs = planBarging.objects.filter(
            iup_id=iup_id,
            date_plan=current_date,
            category=category,
        )

        if vendor_code:
            return qs.filter(vendor_code=vendor_code)

        return qs.filter(vendor_code__isnull=True) | qs.filter(vendor_code="")

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
        category = data.get("category") or "BARGING"
        vendor_code = self._normalize_vendor_code(data)

        if not iup_id:
            return Response(
                {"iup": ["IUP wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicates = []
        check_date = start

        while check_date <= end:
            if self._duplicate_queryset(iup_id, check_date, category, vendor_code).exists():
                duplicates.append(check_date.isoformat())

            check_date += timedelta(days=1)

        if duplicates:
            return Response(
                {
                    "detail": "Plan Barging sudah ada pada beberapa tanggal.",
                    "duplicates": duplicates,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_lim = float(data.get("lim") or 0)
        total_sap = float(data.get("sap") or 0)

        daily_lim = total_lim / days_count if days_count else 0
        daily_sap = total_sap / days_count if days_count else 0

        created = []
        current = start

        while current <= end:
            row_data = data.copy()

            row_data["iup"] = iup_id
            row_data["date_plan"] = current.isoformat()
            row_data["category"] = category
            row_data["vendor_code"] = vendor_code
            row_data["lim"] = daily_lim
            row_data["sap"] = daily_sap

            row_data.pop("date_start", None)
            row_data.pop("date_end", None)
            row_data.pop("vendors", None)

            code = f"PB-{current.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            serializer = self.get_serializer(data=row_data)
            serializer.is_valid(raise_exception=True)

            serializer.save(
                code=code,
                user=request.user if request.user.is_authenticated else None,
            )

            created.append(serializer.data)
            current += timedelta(days=1)

        return Response(
            {
                "count": len(created),
                "results": created,
            },
            status=status.HTTP_201_CREATED,
        )

    def handle_export(self, request):
        params = {}

        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="mining.plan_barging",
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