from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from mining.models import MiningActivity, MiningActivityCategories
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from core.base import BaseViewSet
from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer
from master.api.pagination import StandardResultsSetPagination

from .serializers import MiningActivitySerializer, MiningActivityCategorySerializer
from .filters import activityFilter

class MiningActivityViewSet(BaseViewSet):
    queryset = MiningActivity.objects.all().order_by("code")
    serializer_class = MiningActivitySerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = activityFilter

    search_fields = [
        "code",
        "name",
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
    ]

    soft_delete_field = None

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="mining.activity",
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
            "master_activity_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="master_activity_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

class MiningActivityCategoriesViewSet(BaseViewSet):
    queryset = MiningActivityCategories.objects.all().order_by("code")
    serializer_class = MiningActivityCategorySerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
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
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
    ]

    soft_delete_field = None