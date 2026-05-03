from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from master.models import SourceMinesDumping
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission, user_allowed_iup_ids
from .serializers import SourceMinesDumpingSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class SourceMinesDumpingViewSet(MasterBaseViewSet):
    queryset = SourceMinesDumping.objects.select_related("iup").all().order_by("dumping_point")
    serializer_class = SourceMinesDumpingSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]

    # iup_code/iup_name itu lewat FK -> pakai iup__...
    search_fields    = ["dumping_point", "iup__iup_code", "iup__iup_name"]

    ordering_fields  = ["id", "dumping_point",  "latitude", "longitude"]

    # Export/Template disesuaikan field SourceMines (hapus center_lat/center_lng/default_zoom)
    export_fields    = [
        "id",
        "iup_code",
        "iup_name",
        "dumping_point",
        "latitude",
        "longitude",
        "geometry",
    ]

    # Template header: kolom yang user isi saat import
    # Biasanya pakai iup_code agar mudah (bukan iup id)
    template_headers = [
        "iup_code",
        "dumping_point",
        "latitude",
        "longitude",
        "geometry",
        "description",
        "category",
        "compositing",
        "status",
    ]

    # soft_delete_field = None
    soft_delete_field = "is_deleted"
    
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
        qs = super().get_queryset()
        user = self.request.user
        iup_id = self._get_iup_id_param()

        # system / superuser
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        # site user: default ke active_iup kalau param kosong
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.DumpingPoints",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response({"status": "import queued", "job_id": str(job.id)}, status=202)

    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "Dumping_point_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Dumping_point_import_template.xlsx"
        )