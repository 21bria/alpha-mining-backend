from django.db import connection, IntegrityError
from django.http import FileResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework.exceptions import ValidationError
import os

from master.models import SourcePitDome
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)

from .serializers import SourcePitDomeSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet


class SourcePitDomeViewSet(MasterBaseViewSet):
    queryset = (
        SourcePitDome.objects
        .select_related(
            "loading_point",
            "loading_point__iup",
            "user",
        )
        .all()
        .order_by("dome")
    )

    serializer_class = SourcePitDomeSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "dome",
        "dome_type",
        "description",
        "compositing",
        "status_dome",
        "loading_point__loading_point",
        "loading_point__iup__iup_code",
        "loading_point__iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "dome",
        "dome_type",
        "status_dome",
        "is_active",
        "latitude",
        "longitude",
    ]

    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "loading_point_label",
        "dome",
        "dome_type",
        "description",
        "compositing",
        "status_dome",
        "is_active",
        "direct_sale",
        "latitude",
        "longitude",
        "geometry",
    ]

    template_headers = [
        "iup_code",
        "loading_point",
        "dome",
        "dome_type",
        "description",
        "compositing",
        "status_dome",
        "is_active",
        "direct_sale",
        "latitude",
        "longitude",
        "geometry",
    ]

    def _get_iup_id_param(self):
        return (
            self.request.query_params.get("iup_id")
            or self.request.query_params.get("iup")
        )

    def _get_loading_point_param(self):
        return (
            self.request.query_params.get("loading_point")
            or self.request.query_params.get("loading_point_id")
            or self.request.query_params.get("id_loading")
        )

    def _get_active_iup_id_for_user(self, user):
        active = getattr(user, "active_iup_id", None) or getattr(user, "iup_id", None)
        if active:
            return str(active)

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return None

        allowed_list = list(allowed)
        return str(allowed_list[0]) if allowed_list else None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self._get_iup_id_param()
        loading_point_id = self._get_loading_point_param()

        if loading_point_id:
            qs = qs.filter(loading_point_id=loading_point_id)

        # system / superuser
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            if iup_id:
                qs = qs.filter(loading_point__iup_id=iup_id)
            return qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(loading_point__iup_id__in=allowed)

        # site user default ke active IUP kalau param kosong
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(loading_point__iup_id=iup_id)

        return qs

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.source_pit_dome",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "import queued", "job_id": str(job.id)},
            status=202,
        )

    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "SourcePitDome_import_template.xlsx",
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="SourcePitDome_import_template.xlsx",
        )


    def perform_create(self, serializer):
        user = self.request.user
        loading_point = serializer.validated_data.get("loading_point")

        if not (
            getattr(user, "is_system", False)
            or getattr(user, "is_superuser", False)
            or getattr(user, "is_management", False)
        ):
            allowed = user_allowed_iup_ids(user)

            if not loading_point or loading_point.iup_id not in allowed:
                raise ValidationError({
                    "loading_point": "Anda tidak punya akses ke IUP loading point ini."
                })

        serializer.save(user=user)

    def perform_update(self, serializer):
        user = self.request.user
        loading_point = serializer.validated_data.get(
            "loading_point",
            serializer.instance.loading_point,
        )

        if not (
            getattr(user, "is_system", False)
            or getattr(user, "is_superuser", False)
            or getattr(user, "is_management", False)
        ):
            allowed = user_allowed_iup_ids(user)

            if not loading_point or loading_point.iup_id not in allowed:
                raise ValidationError({
                    "loading_point": "Anda tidak punya akses ke IUP loading point ini."
                })

        serializer.save(user=user)