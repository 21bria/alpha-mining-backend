from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os

from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from mining.models import FuelConsumption,FuelConsumptionView

from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from analytics.models import ExportJob
from analytics.tasks import run_export_job

from core.permissions import (
    GlobalMasterPermission, 
    RoleReadOnlyForViewer, 
    IUPObjectPermission,
    user_allowed_iup_ids
    )
from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from .serializers import FuelConsumptionSerializer
from .filters import FuelFilter

class FuelConsumptionViewSet(BaseViewSet):
    queryset = FuelConsumptionView.objects.all().order_by("date")
    serializer_class = FuelConsumptionSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = FuelFilter

    search_fields = [
        "date",
        "code",
        "category",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "date",
        "code",
        "category",
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
    
class FuelConsumptionViewCRUDSet(BaseViewSet):
    queryset = FuelConsumption.objects.all()
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination

    soft_delete_field = "is_deleted"
    range_delete_field = "date"
    range_delete_iup_field = "iup_id"

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="mining.fuel_daily",
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
            module="mining.fuel_consumption",
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
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "mining_fuel_transpose_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response({"detail": "Template file not found"}, status=404)

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="mining_fuel_transpose_import_template.xlsx",
        )