from django.db import connection
from django.http import FileResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
import os
from rest_framework.decorators import action
from mining.models import MiningActivityLocation
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.base import BaseViewSet
from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
)
from master.api.pagination import StandardResultsSetPagination
from .serializers import MiningActivityLocationSerializer


class MiningActivityLocationViewSet(BaseViewSet):
    queryset = (
        MiningActivityLocation.objects
        .select_related("iup", "user")
        .all()
        .order_by("code")
    )
    serializer_class = MiningActivityLocationSerializer
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

    search_fields = [
        "code",
        "name",
        "description",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
        "created_at",
        "updated_at",
    ]

    export_fields = [
        "id",
        "code",
        "iup_code",
        "iup_name",
        "name",
        "description",
        "username",
        "created_at",
    ]

    soft_delete_field = None

    def get_queryset(self):
        qs = MiningActivityLocation.objects.select_related("iup", "user").all()

        if hasattr(MiningActivityLocation, "is_deleted"):
            qs = qs.filter(is_deleted=False)

        return qs.order_by("code")

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.activities_locations",
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

    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "master_activity_locations_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="master_activity_locations_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )