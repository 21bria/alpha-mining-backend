from django.db import connection
from django.http import FileResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
import os
from rest_framework.decorators import action
from mining.models import mineAdditionFactor
from .serializers import FillFactorSerializer

from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
)
from master.api.pagination import StandardResultsSetPagination
from core.base import BaseViewSet


class FillFactorViewSet(BaseViewSet):
    queryset = mineAdditionFactor.objects.select_related("iup", "user").all().order_by("id")
    serializer_class = FillFactorSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "code",
        "type_unit",
        "material",
        "validation",
        "description",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "code",
        "type_unit",
        "material",
        "density_bcm",
        "density_lcm",
        "bucket_capacity",
        "created_at",
        "updated_at",
    ]

    export_fields = [
        "id",
        "code",
        "iup_code",
        "iup_name",
        "type_unit",
        "material",
        "density_bcm",
        "density_lcm",
        "bucket_capacity",
        "validation",
        "description",
        "username",
        "created_at",
    ]

    soft_delete_field = None

    def get_queryset(self):
        qs = mineAdditionFactor.objects.select_related("iup", "user").all()

        if hasattr(mineAdditionFactor, "is_deleted"):
            qs = qs.filter(is_deleted=False)

        return qs.order_by("id")
    
    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "mining_fill_factors_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="mining_fill_factors_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="mining.fill_factor",
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
    
    