from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from geology.models import SampleProductions,SamplesView

from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission,user_allowed_iup_ids
from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from master.models import SampleType
from .serializers import SamplesSerializer,SamplesCRUDSerializer
from .filters import SamplesFilter

from analytics.models import ExportJob
from analytics.tasks import run_export_job


def get_sample_types(categories=None):
    qs = SampleType.objects.filter(status=1)

    if categories:
        qs = qs.filter(category__in=categories)

    return list(qs.values_list("type_sample", flat=True))


class SamplesViewSet(BaseViewSet):
    queryset = SamplesView.objects.none()
    serializer_class = SamplesSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = SamplesFilter

    search_fields = [
        "date_sample",
        "sample_id",
        "material",
        "batch",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "date_sample",
        "sample_id",
        "material",
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
        sample_types = get_sample_types(["production", "geology"])

        qs = (
            self.queryset.model.objects
            .filter(type_sample__in=sample_types)
            .order_by("date_sample")
        )

        user = self.request.user
        iup_id = self._get_iup_id_param()

        # SYSTEM / SUPERUSER
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        # SITE USER
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

class SamplesViewCRUDSet(BaseViewSet):
    serializer_class = SamplesCRUDSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "tgl_sample",
        "sample_number",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "tgl_sample",
        "sample_number",
    ]

    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "tgl_sample",
        "sample_number",
    ]

    soft_delete_field = "is_deleted"
    range_delete_field = "tgl_sample"
    range_delete_iup_field = "iup_id"

    def get_queryset(self):
        sample_types = get_sample_types(["production", "geology"])
        return (
            SampleProductions.objects
            .select_related("iup")
            .filter(is_deleted=False, type__in=sample_types)
            .order_by("tgl_sample")
        )

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="geology.samples",
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
            "geology_samples_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="geology_samples_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="geology.sample",
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
