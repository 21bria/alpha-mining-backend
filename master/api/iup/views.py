from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters
from master.models import MineIUP
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from rest_framework.permissions import AllowAny, IsAuthenticated
from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission, user_allowed_iup_ids
from .serializers import MineIUPSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class MineIUPViewSet(MasterBaseViewSet):
    queryset = MineIUP.objects.all().order_by("iup_name")
    serializer_class = MineIUPSerializer
    # permission_classes = [AllowAny]
     
    permission_classes = [IsAuthenticated, GlobalMasterPermission]
    
    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["iup_name", "iup_code"]
    ordering_fields  = ["id", "iup_name"]

    export_fields    = ["id", "iup_code", "iup_name", "geometry", "center_lat", "center_lng", "default_zoom"]
    template_headers = ["iup_code", "iup_name", "geometry", "center_lat", "center_lng", "default_zoom"]

    soft_delete_field = None

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.MineIUP",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        # ambil schema tenant aktif
        schema_name = connection.schema_name

        # kirim schema + job_id ke celery
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "import queued", "job_id": str(job.id)},
            status=202
        )

    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "IUP_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="IUP_import_template.xlsx"
        )