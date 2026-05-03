from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os

from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticated
from core.permissions import GlobalMasterPermission
from geology.models import sampleCrmRoaView
from rest_framework.permissions import IsAuthenticated
from .serializers import sampleCrmRoaViewSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet
from .filters import RoaFilter
# export
from analytics.models import ExportJob
from analytics.tasks import run_export_job

class sampleCrmRoaviewSet(MasterBaseViewSet):
    queryset = sampleCrmRoaView.objects.all().order_by("oreas_name")
    serializer_class = sampleCrmRoaViewSerializer
    permission_classes = [IsAuthenticated, GlobalMasterPermission]

    pagination_class = StandardResultsSetPagination

    filter_backends  = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class  = RoaFilter
    search_fields    = ["oreas_name","sample_number"]
    ordering_fields  = ["id", "oreas_name"]


    soft_delete_field = None

    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="sample_crm.roa",
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