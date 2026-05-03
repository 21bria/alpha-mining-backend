from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters,status
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission,user_allowed_iup_ids
from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet

from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from analytics.models import ExportJob
from analytics.tasks import run_export_job


from selling.models import BargingPlan
from .serializers import BargingPlanSerializer
from .filters import SellingFilter

from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
)


class BargingPlanViewSet(BaseViewSet):
    queryset = BargingPlan.objects.all().order_by("-plan_date", "-created_at")
    serializer_class = BargingPlanSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = SellingFilter

    filterset_fields = {
        "iup_id": ["exact"],
        "plan_date": ["exact", "gte", "lte"],
        "barge_code": ["exact", "icontains"],
        "tugboat_name": ["exact", "icontains"],
        "no_plan": ["exact", "gte", "lte"],
        "created_at": ["exact", "gte", "lte"],
    }

    search_fields = [
        "code",
        "iup_code",
        "iup_name",
        "barge_code",
        "tugboat_name",
        "description",
    ]

    ordering_fields = [
        "id",
        "code",
        "plan_date",
        "barge_code",
        "tugboat_name",
        "tonnage_plan",
        "no_plan",
        "created_at",
        "updated_at",
        "iup_code",
        "iup_name",
    ]
    ordering = ["-plan_date", "-created_at"]

    soft_delete_field = "is_deleted"
    range_delete_field = "plan_date"
    range_delete_iup_field = "iup_id"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="selling.barging_plan",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "import queued", "job_id": str(job.id)},
            status=status.HTTP_202_ACCEPTED
        )

    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="selling.barging_plan",
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
            "barging_plan_transpose_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="barging_plan_transpose_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )