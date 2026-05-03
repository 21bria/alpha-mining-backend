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

from selling.models import SellingDetailsBargingView,SellingBarging
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from .serializers import SellingBargingSerializer,SellingBargingImportDeleteSerializer
from .filters import SellingFilter

from analytics.models import ExportJob
from analytics.tasks import run_export_job

class SellingViewSet(BaseViewSet):
    queryset = SellingDetailsBargingView.objects.none()
    serializer_class = SellingBargingSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = SellingFilter

    # search pakai field yang benar
    search_fields = [
        "date_hauling",
        "barge_code",
        "material",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "date_hauling",
        "barge_code",
        "material"
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
        qs = (
            self.queryset.model.objects
            .order_by("date_hauling")
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
    
class SellingBargingCRUDViewSet(BaseViewSet):
    queryset = SellingBarging.objects.all().order_by("-id")
    serializer_class = SellingBargingImportDeleteSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = {
        "iup_id": ["exact"],
        "created_at": ["exact", "gte", "lte"],
        "user__username": ["exact", "icontains"],
    }

    search_fields = [
        "iup_code",
        "iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "created_at",
        "iup_code",
        "iup_name",
        "user__username",
    ]
    ordering = ["-id"]

    template_file = "master/import_templates/selling_barging_import_template.xlsx"

    soft_delete_field = "is_deleted"
    range_delete_field = "date_hauling"
    range_delete_iup_field = "iup_id"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="selling.barging",
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
            module="selling.details_barging",
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
            "selling_barging_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="selling_barging_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )