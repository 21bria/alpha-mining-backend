from django.db import connection, IntegrityError
from django.http import FileResponse
from django.conf import settings
import os

from rest_framework import filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action

from mining.models import MiningActivityLocation
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

from .serializers import MiningActivityLocationSerializer


def pick_one_iup_id(user):
    allowed = user_allowed_iup_ids(user) or set()
    return next(iter(allowed), None)


class MiningActivityLocationViewSet(MasterBaseViewSet):
    queryset = (
        MiningActivityLocation.objects
        .select_related("iup", "user")
        .all()
        .order_by("code")
    )

    serializer_class = MiningActivityLocationSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "code",
        "name",
        "description",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
        "created_at",
        "updated_at",
    ]

    export_fields = [
        "id",
        "code",
        "iup_code",
        "iup_name",
        "name",
        "description",
        "username",
        "created_at",
    ]

    soft_delete_field = None

    def _get_iup_id_param(self):
        return (
            self.request.query_params.get("iup_id")
            or self.request.query_params.get("iup")
        )

    def _get_active_iup_id_for_user(self, user):
        active_iup_id = (
            getattr(user, "active_iup_id", None)
            or getattr(user, "iup_id", None)
        )

        if active_iup_id:
            return str(active_iup_id)

        allowed = user_allowed_iup_ids(user)

        if not allowed:
            return None

        return str(next(iter(allowed), None)) or None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        iup_id = self._get_iup_id_param()

        if (
            getattr(user, "is_system", False)
            or getattr(user, "is_superuser", False)
        ):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)

        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        is_privileged = (
            getattr(user, "is_system", False)
            or getattr(user, "is_management", False)
            or getattr(user, "is_superuser", False)
        )

        if not is_privileged:
            iup_id = (
                getattr(user, "active_iup_id", None)
                or getattr(user, "iup_id", None)
                or pick_one_iup_id(user)
            )

            if not iup_id:
                raise ValidationError({
                    "iup": "IUP aktif user tidak ditemukan.",
                })

            # Masukkan sebelum serializer.is_valid()
            data["iup"] = iup_id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
        except IntegrityError as exc:
            message = str(exc)

            if "name" in message:
                raise ValidationError({
                    "name": (
                        "Activity location sudah ada "
                        "untuk IUP ini."
                    ),
                })

            if "code" in message:
                raise ValidationError({
                    "code": "Code activity location sudah digunakan.",
                })

            raise

        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.activities_locations",
            file=file,
            created_by=(
                request.user
                if request.user.is_authenticated
                else None
            ),
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {
                "status": "import queued",
                "job_id": str(job.id),
            },
            status=202,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="download-template",
    )
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "master_activity_locations_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": "Template file not found."},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="master_activity_locations_import_template.xlsx",
        )