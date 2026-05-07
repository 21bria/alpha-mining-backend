from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from geology.models import OreProductions,OreProductionsView

from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission,user_allowed_iup_ids
from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from .serializers import ProductionsSerializer,ProductionsCRUDSerializer
from .filters import ProductionsFilter
# export
from analytics.models import ExportJob
from analytics.tasks import run_export_job


class ProductionsViewSet(BaseViewSet):
    queryset = OreProductionsView.objects.all()
    ordering_fields = ["tgl_production"]
    ordering = ["-tgl_production"]

    serializer_class = ProductionsSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    
    pagination_class = StandardResultsSetPagination
    filter_backends  = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class   = ProductionsFilter

    search_fields = [
        "tgl_production",
        "sample_number",
        "nama_material",
        "batch_code",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "tgl_production",
        "sample_number",
        "nama_material",
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
        qs = self.queryset.order_by("tgl_production")
        user = self.request.user
        iup_id = self._get_iup_id_param()

        # SYSTEM / SUPERUSER
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        # SITE USER
        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        # MANAGEMENT / GLOBAL VIEWER
        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs
    
class ProductionsViewCRUDSet(BaseViewSet):
    queryset = OreProductions.objects.filter(is_deleted=False)
    serializer_class = ProductionsCRUDSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "tgl_production",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "tgl_production",
    ]

    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "tgl_production",
    ]

    soft_delete_field = "is_deleted"
    range_delete_field = "tgl_production"
    range_delete_iup_field = "iup_id"

    def get_queryset(self):
        return (
            OreProductions.objects
            .select_related("iup")
            .filter(is_deleted=False)
            .order_by("tgl_production")
        )
    
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

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response(
                {"detail": "Payload must be a list of objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not data:
            return Response(
                {"detail": "Payload is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        iup_id = (
            request.query_params.get("iup_id")
            or request.query_params.get("iup")
        )

        # SYSTEM / SUPERADMIN / MANAGEMENT
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):

            if not iup_id:
                return Response(
                    {"detail": "IUP is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # SITE USER
        else:
            iup_id = self._get_active_iup_id_for_user(user)

            if not iup_id:
                return Response(
                    {"detail": "No active IUP for current user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # inject iup ke semua row
        for row in data:
            row["iup"] = iup_id

        serializer = self.get_serializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instances = serializer.save()

        return Response(
            {
                "detail": "Bulk ore productions created successfully.",
                "count": len(instances),
            },
            status=status.HTTP_201_CREATED,
        )
    
    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="geology.ore",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "import queued", "job_id": str(job.id)},
            status=202
        )
    
    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="geology.ore",
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
            "geology_ore_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="geology_ore_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
  