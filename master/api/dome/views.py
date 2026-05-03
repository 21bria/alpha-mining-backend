from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters

from master.models import SourceMinesDome
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission
from .serializers import SourceMinesDomeSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet

from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from core.permissions import user_allowed_iup_ids

def pick_one_iup_id(user):
    allowed = user_allowed_iup_ids(user) or set()
    return next(iter(allowed), None)

class SourceMinesDomeViewSet(MasterBaseViewSet):
    queryset = SourceMinesDome.objects.select_related("iup", "dumping").all().order_by("pile_id")
    serializer_class = SourceMinesDomeSerializer
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
        "pile_id",
        "category",
        "description",
        "iup__iup_code",
        "iup__iup_name",
        "dumping__dumping_point",
    ]

    ordering_fields = [
        "id",
        "pile_id",
        "category",
        "status",
        "latitude",
        "longitude"
    ]

    # Export fields (sesuaikan untuk excel export)
    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "pile_id",
        "dumping_label", 
        "category",
        "description",
        "status",
        "latitude",
        "longitude",
        "geometry",
    ]

    # Template import header (yang user isi)
    # Rekomendasi: pakai iup_code biar mudah, plus source bisa by "source_code" atau "source_area" (tergantung importer)
    template_headers = [
        "iup_code",
        "pile_id",
        "dumping_point", 
        "category",
        "description",
        "status",
        "latitude",
        "longitude",
        "geometry",
        # optional kalau import perlu mapping source:
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

        try:
            return str(next(iter(allowed)))
        except TypeError:
            allowed_list = list(allowed)
            return str(allowed_list[0]) if allowed_list else None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        iup_id = self._get_iup_id_param()

        # system / superuser
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        # site user: default ke active_iup kalau param kosong
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs
    
    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.source_mines_dome",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response({"status": "import queued", "job_id": str(job.id)}, status=202)

    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "master",
            "import_templates",
            "SourceMinesDome_import_template.xlsx",
        )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="SourceMinesDome_import_template.xlsx",
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
            # ini optional, tapi enak supaya pesannya tepat
            if "uq_pile_id_per_iup" in msg or "pile_id" in msg:
                raise ValidationError({"pile_id": "Loading point sudah ada untuk IUP ini."})
            if "code_key" in msg or "code" in msg:
                raise ValidationError({"pile_id": "Loading point sudah ada (duplicate code)."})
            raise