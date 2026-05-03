from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action

from django.db.models import Count, Sum
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticated
from mining.models import HmUnit
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from .serializers import (
    HmUnitListSerializer,
    HmUnitRetrieveSerializer,
    HmUnitWriteSerializer,
)
from core.base import BaseViewSet
from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids
)
from master.api.pagination import StandardResultsSetPagination
from .filters import acitvityFilter

class HmUnitViewSet(BaseViewSet):
    queryset = (
        HmUnit.objects
        .select_related("iup", "unit", "user")
        .prefetch_related(
            "details",
            "details__status",
            "details__activity",
            "details__location",
            "details__user",
        )
        .annotate(
            total_details=Count("details", distinct=True),
            total_duration_min=Sum("details__duration_min"),
        )
        .order_by("-date", "shift")
    )

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = acitvityFilter


    search_fields = [
        "date",
        "shift",
        "status",
        "unit__unit_code",
        "unit__unit_model",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "date",
        "shift",
        "hm_start",
        "hm_end",
        "status",
        "unit__unit_code",
    ]

    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "unit_code",
        "unit_model",
        "date",
        "shift",
        "hm_start",
        "hm_end",
        "status",
        "username",
    ]

    soft_delete_field = None

   
    def _get_iup_id_param(self):
        return self.request.query_params.get("iup_id") or self.request.query_params.get("iup")

    def _get_active_iup_id_for_user(self, user):
        active = getattr(user, "active_iup_id", None) or getattr(user, "iup_id", None)
        if active:
            return str(active)

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return None

        # allowed bisa list / set -> aman untuk dua-duanya
        try:
            return str(next(iter(allowed)))
        except TypeError:
            # fallback kalau aneh
            allowed_list = list(allowed)
            return str(allowed_list[0]) if allowed_list else None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self._get_iup_id_param()

        # SYSTEM/superuser: boleh semua, tapi kalau ada iup_id tetap filter
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        # SITE_USER: auto pakai iup aktif kalau param tidak dikirim
        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        # MANAGEMENT / GLOBAL_VIEWER: kalau dikirim iup_id, filter
        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs


    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="mining.activity_units",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response({"status": "import queued", "job_id": str(job.id)}, status=202)

    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "mining_activities_units_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="mining_activities_units_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    def get_serializer_class(self):
        if self.action == "list":
            return HmUnitListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return HmUnitWriteSerializer
        return HmUnitRetrieveSerializer