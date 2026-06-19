from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters
from core.permissions import GlobalMasterPermission
from master.models import Material
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from rest_framework.permissions import IsAuthenticated
from .serializers import MaterialSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class MaterialViewSet(MasterBaseViewSet):
    queryset = Material.objects.all().order_by("name")
    serializer_class = MaterialSerializer    
    permission_classes = [IsAuthenticated, GlobalMasterPermission]


    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["name","is_production","is_ore","sale_adjust","description"]
    ordering_fields  = ["id", "name"]

    export_fields    = ["id", "name","is_production","is_ore","sale_adjust","description"]
    template_headers = ["name", "description"]

    soft_delete_field = None


    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.Material",
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
            "Material_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Material_import_template.xlsx"
        )