from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from geology.models import Waybills,listWaybills
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import (
    GlobalMasterPermission, 
    RoleReadOnlyForViewer, 
    IUPObjectPermission,
    user_allowed_iup_ids
    )
from .serializers import WaybillsSerializer,WaybillsCRUDSerializer
from master.api.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from .filters import WaybillFilter

# export
from analytics.models import ExportJob
from analytics.tasks import run_export_job

class WaybillsViewSet(BaseViewSet):
    queryset = listWaybills.objects.all().order_by("tgl_deliver")
    serializer_class = WaybillsSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = WaybillFilter

    # search pakai field yang benar
    search_fields = [
        "waybill_number",
        "tgl_deliver",
        "sample_id",
        "sample_status",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "waybill_number",
        "tgl_deliver",
        "sample_id",
        "sample_status"
    ]

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

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        iup_id = self._get_iup_id_param()

        if getattr(user, "is_superuser", False) or getattr(user, "role", None) == "SYSTEM":
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        if getattr(user, "role", None) == "SITE" and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

class WaybillsViewCRUDSet(BaseViewSet):
    queryset = Waybills.objects.select_related("iup").all().order_by("tgl_deliver")
    serializer_class = WaybillsCRUDSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination

    search_fields = [
        "waybill_number",
        "tgl_deliver",
        "sample_id",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "waybill_number",
        "tgl_deliver",
        "sample_id",
    ]

    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "tgl_deliver",
        "waybill_number",
        "sample_id",
    ]

    soft_delete_field = "is_deleted"
    range_delete_field = "tgl_deliver"
    range_delete_iup_field = "iup_id"
    
    def get_queryset(self):
        return Waybills.objects.filter(is_deleted=False)

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="geology.waybills",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response({"status": "import queued", "job_id": str(job.id)}, status=202)

    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="geology.waybills",
            params=params,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_export_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "export queued", "job_id": str(job.id)},
            status=202
        )
    
    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "geology_waybills_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="geology_waybills_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    