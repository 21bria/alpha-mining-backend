from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters

from master.models import SellingCode
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission
from .serializers import SellingCodeSerializer
from master.api.pagination import StandardResultsSetPagination
from core.base import BaseViewSet

from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from core.permissions import user_allowed_iup_ids

# export
from analytics.models import ExportJob
from analytics.tasks import run_export_job

import logging
logger = logging.getLogger(__name__)

def pick_one_iup_id(user):
    allowed = user_allowed_iup_ids(user) or set()
    return next(iter(allowed), None)

class SellingCodeViewSet(BaseViewSet):
    queryset = SellingCode.objects.select_related("iup").all().order_by("code")
    serializer_class = SellingCodeSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # search pakai field yang benar
    search_fields = [
        "code",
        "type",
        "description",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "code",
        "type",
        "active"
    ]
    soft_delete_field = "is_deleted"  # kalau ada di BaseTenantModel

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


    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "master_selling_code_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="master_selling_code_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="master.selling_code",
            params=params,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        try:
            run_export_job.delay(schema_name, str(job.id))
        except Exception as e:
            job.status = "failed"
            job.message = f"Queue error: {e}"
            job.save(update_fields=["status", "message"])
            return Response(
                {"detail": f"Gagal mengirim export job ke queue: {e}"},
                status=500
            )

        return Response(
            {"status": "export queued", "job_id": str(job.id)},
            status=202
        )
    
    def perform_create(self, serializer):
        user = self.request.user

        try:
            # SYSTEM/MANAGEMENT/SUPERUSER: biarkan dari payload
            if getattr(user, "is_system", False) or getattr(user, "is_management", False) or getattr(user, "is_superuser", False):
                serializer.save()
                return

            # SITE_USER / non-system: server set iup otomatis
            iup_id = getattr(user, "active_iup_id", None) or getattr(user, "iup_id", None) or pick_one_iup_id(user)
            if not iup_id:
                raise ValidationError({"iup": "IUP aktif user tidak ditemukan."})

            serializer.save(iup_id=iup_id)

        except IntegrityError as e:
            msg = str(e)
            if "code_key" in msg or "code" in msg:
                raise ValidationError({"code": "Code sudah ada untuk IUP ini."})
            raise