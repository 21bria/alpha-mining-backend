from django.db import connection
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from selling.models import SellingOfficialView,SellingOfficial
from .serializers import SellingOfficialViewSerializer,SellingOfficialSerializer
from core.base import BaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer,user_allowed_iup_ids
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

# export
from analytics.models import ExportJob
from analytics.tasks import run_export_job

class SellingOfficialViewSet(BaseViewSet):
    queryset = SellingOfficialView.objects.all().order_by("-id")
    serializer_class = SellingOfficialViewSerializer
    permission_classes = [IsAuthenticated, GlobalMasterPermission, RoleReadOnlyForViewer]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = [
        "type_selling",
        "id_factory",
        "start_date",
        "end_date",
        "re_assay",
    ]

    search_fields = [
        "name_surveyor",
        "factory_stock",
        "so_number",
        "product_code",
        "barge_code",
        # "description",
        "type_selling",
        "user_name",
    ]

    ordering_fields = [
        "id",
        "name_surveyor",
        "factory_name",
        "so_number",
        "product_code",
        "barge_code",
        "type_selling",
        "tonnage",
        "ni",
        "co",
        "fe",
        "mgo",
        "sio2",
        "mc",
        "start_date",
        "end_date",
        "re_assay",
        "user_name",
    ]
    ordering = ["-id"]

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
    
class SellingOfficialCRUDViewSet(BaseViewSet):
    queryset = SellingOfficial.objects.select_related( "surveyor", "user").all().order_by("-id")
    serializer_class = SellingOfficialSerializer
    permission_classes = [IsAuthenticated, GlobalMasterPermission, RoleReadOnlyForViewer]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = [
        "surveyor",
        "type_selling",
        "official",
        "id_factory",
        "re_assay",
        "start_date",
        "end_date",
    ]

    search_fields = [
        "so_number",
        "product_code",
        "barge_code",
        "official",
        "description",
        "type_selling",
        "surveyor__surveyor",
    ]

    ordering_fields = [
        "id",
        "so_number",
        "product_code",
        "barge_code",
        "type_selling",
        "official",
        "tonnage",
        "start_date",
        "end_date",
        "re_assay",
    ]
    
    ordering = ["-id"]

    soft_delete_field = "is_deleted"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="selling.official",
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
            module="selling.official",
            params=params,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        try:
            run_export_job.delay(schema_name, str(job.id))
        except Exception as e:
            job.status = "failed"
            job.message = f"Queue error: {e}"
            job.save(update_fields=["status", "message"])
            return Response(
                {"detail": f"Gagal mengirim export job ke queue: {e}"},
                status=500
            )

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
            "selling_official_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="selling_official_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )