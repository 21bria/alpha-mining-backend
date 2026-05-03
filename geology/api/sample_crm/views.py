from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework import filters, status
from rest_framework.permissions import IsAuthenticated
from core.permissions import GlobalMasterPermission
from geology.models.geology_sample_crm_certified import SampleCrmCertified
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from rest_framework.permissions import IsAuthenticated
from .serializers import CRMCertificateSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

class CRMCertificateViewSet(MasterBaseViewSet):
    queryset = SampleCrmCertified.objects.all().order_by("oreas_name")
    serializer_class = CRMCertificateSerializer
    permission_classes = [IsAuthenticated, GlobalMasterPermission]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["oreas_name"]
    ordering_fields = ["id", "oreas_name"]

    export_fields = [
        "id",
        "oreas_name",
        "ni",
        "co",
        "al2o3",
        "cao",
        "cr2o3",
        "fe2o3",
        "fe",
        "k2o",
        "mgo",
        "mno",
        "na2o",
        "p2o5",
        "p",
        "sio2",
        "tio2",
        "s",
        "cu",
        "zn",
        "ci",
        "so3",
        "loi",
        "sm",
    ]

    template_headers = [
        "oreas_name",
        "ni",
        "co",
        "al2o3",
        "cao",
        "cr2o3",
        "fe2o3",
        "fe",
        "k2o",
        "mgo",
        "mno",
        "na2o",
        "p2o5",
        "p",
        "sio2",
        "tio2",
        "s",
        "cu",
        "zn",
        "ci",
        "so3",
        "loi",
        "sm",
    ]

    soft_delete_field = None

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="geology.SampleCrmCertified",
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

    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "geology",
            "import_templates",
            "CRM_certificate_import_template.xlsx"
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": "Template file not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="CRM_certificate_import_template.xlsx"
        )