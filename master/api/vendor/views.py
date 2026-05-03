from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters
from core.permissions import GlobalMasterPermission
from master.models import Vendors
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from rest_framework.permissions import IsAuthenticated
from .serializers import VendorsSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class VendorsViewSet(MasterBaseViewSet):
    queryset = Vendors.objects.all().order_by("vendor_name")
    serializer_class = VendorsSerializer    
    permission_classes = [IsAuthenticated, GlobalMasterPermission]


    pagination_class = StandardResultsSetPagination
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["code","vendor_name", "description"]
    ordering_fields  = ["id", "vendor_name"]

    export_fields    = ["id","code","vendor_name","status","description"]
    template_headers = ["code","vendor_name","status","description"]

    soft_delete_field = None


    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.vendors",
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
            "Vendors_import_template.xlsx"
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="Vendors_import_template.xlsx"
        )