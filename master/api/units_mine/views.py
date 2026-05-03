from django.db import connection
from django.http import FileResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import os
from rest_framework.decorators import action
from rest_framework import filters
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from master.models import MineUnits, UnitAssignment, unitsCategories
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job
from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer,user_allowed_iup_ids
from .serializers import (
    MineUnitsSerializer,
    UnitAssignmentSerializer,
    UnitsCategoriesSerializer,
)
from .filters import UnitsFilter
from master.api.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError
from django.db import IntegrityError, transaction
from django.utils.timezone import now

from analytics.models import ExportJob
from analytics.tasks import run_export_job

def pick_one_iup_id(user):
    allowed = user_allowed_iup_ids(user) or set()
    return next(iter(allowed), None)

class MineUnitsViewSet(BaseViewSet):
    queryset = (
        MineUnits.objects
        .all()
        .prefetch_related("assignments__iup")
        .order_by("unit_code")
    )
    serializer_class = MineUnitsSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = UnitsFilter
    search_fields = [
        "unit_vendor",
        "unit_code",
        "unit_model",
        "unit_class",
        "brand",
        "supports",
        "description",
    ]

    ordering_fields = [
        "id",
        "unit_vendor",
        "unit_code",
        "unit_model",
        "unit_class",
        "brand",
        "status",
        "commisioning_date",
        "on_hire",
        "off_hire",
        "created_at",
    ]

    export_fields = [
        "id",
        "unit_vendor",
        "unit_code",
        "unit_model",
        "unit_class",
        "brand",
        "id_category",
        "id_vendor",
        "supports",
        "status",
        "description",
        "commisioning_date",
        "on_hire",
        "off_hire",
        "active_iup_code",
        "active_iup_name",
    ]

    template_headers = [
        "unit_vendor",
        "unit_code",
        "unit_model",
        "unit_class",
        "brand",
        "id_category",
        "id_vendor",
        "supports",
        "status",
        "description",
        "commisioning_date",
        "on_hire",
        "off_hire",
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
        qs = super().get_queryset()
        user = self.request.user
        iup_id = self._get_iup_id_param()

        # SYSTEM / superuser
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            if iup_id:
                return qs.filter(assignments__iup_id=iup_id).distinct()
            return qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(assignments__iup_id__in=allowed).distinct()

        # site user: default ke active_iup kalau param kosong
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(assignments__iup_id=iup_id).distinct()

        return qs
    
    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="master.mine_units",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response(
            {"status": "import queued", "job_id": str(job.id)},
            status=202
        )
    
    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="master.units",
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
    
    @action(detail=False, methods=["get"], url_path="download-template")
    def download_template(self, request):
        file_path = os.path.join(
            settings.BASE_DIR,
            "imports",
            "templates",
            "master_equipments_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="master_equipments_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    def perform_create(self, serializer):
        user = self.request.user

        try:
            with transaction.atomic():
                unit = serializer.save(user=user)

                iup_id = None

                # SYSTEM / MANAGEMENT / SUPERUSER -> ambil dari payload form
                if (
                    getattr(user, "is_system", False)
                    or getattr(user, "is_management", False)
                    or getattr(user, "is_superuser", False)
                ):
                    raw_iup = self.request.data.get("iup")
                    if raw_iup not in (None, "", "null"):
                        try:
                            iup_id = int(raw_iup)
                        except (TypeError, ValueError):
                            raise ValidationError({"iup": "IUP tidak valid."})

                # SITE_USER -> ambil otomatis dari user
                elif getattr(user, "is_site_user", False):
                    iup_id = (
                        getattr(user, "default_iup_id", None)
                        or getattr(user, "active_iup_id", None)
                        or getattr(user, "iup_id", None)
                        or pick_one_iup_id(user)
                    )

                # kalau ada iup -> buat assignment
                if iup_id:
                    already_active = UnitAssignment.objects.filter(
                        unit=unit,
                        active=True
                    ).exists()

                    if not already_active:
                        UnitAssignment.objects.create(
                            unit=unit,
                            iup_id=iup_id,
                            start_date=now().date(),
                            active=True,
                        )

        except IntegrityError as e:
            msg = str(e)
            if "unit_code" in msg:
                raise ValidationError({"unit_code": "Unit code sudah ada."})
            if "uq_one_active_assignment_per_unit" in msg:
                raise ValidationError({"unit": "Unit ini sudah punya assignment aktif."})
            raise
        
    def perform_update(self, serializer):
        user = self.request.user

        try:
            with transaction.atomic():
                unit = serializer.save()

                iup_id = None

                if (
                    getattr(user, "is_system", False)
                    or getattr(user, "is_management", False)
                    or getattr(user, "is_superuser", False)
                ):
                    raw_iup = self.request.data.get("iup")
                    if raw_iup not in (None, "", "null"):
                        try:
                            iup_id = int(raw_iup)
                        except (TypeError, ValueError):
                            raise ValidationError({"iup": "IUP tidak valid."})

                elif getattr(user, "is_site_user", False):
                    iup_id = (
                        getattr(user, "default_iup_id", None)
                        or getattr(user, "active_iup_id", None)
                        or getattr(user, "iup_id", None)
                        or pick_one_iup_id(user)
                    )

                if iup_id:
                    already_active = UnitAssignment.objects.filter(
                        unit=unit,
                        active=True
                    ).exists()

                    if not already_active:
                        UnitAssignment.objects.create(
                            unit=unit,
                            iup_id=iup_id,
                            start_date=now().date(),
                            active=True,
                        )

        except IntegrityError as e:
            msg = str(e)
            if "unit_code" in msg:
                raise ValidationError({"unit_code": "Unit code sudah ada."})
            raise

class UnitAssignmentViewSet(BaseViewSet):
    queryset = (
        UnitAssignment.objects
        .select_related("unit", "iup")
        .all()
        .order_by("-active", "-start_date")
    )
    serializer_class = UnitAssignmentSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        "unit__unit_code",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "start_date",
        "end_date",
        "active",
    ]

    def perform_create(self, serializer):
        user = self.request.user

        # SITE_USER → otomatis ambil IUP user
        if getattr(user, "is_site_user", False):

            iup_id = (
                getattr(user, "default_iup_id", None)
                or getattr(user, "active_iup_id", None)
                or getattr(user, "iup_id", None)
            )

            if not iup_id:
                allowed = user_allowed_iup_ids(user) or set()
                iup_id = next(iter(allowed), None)

            if not iup_id:
                raise ValidationError({
                    "iup": "User belum punya IUP aktif/default."
                })

            serializer.save(iup_id=iup_id)
            return

        # SYSTEM / MANAGEMENT
        serializer.save()

class UnitsCategoriesViewSet(BaseViewSet):
    queryset = unitsCategories.objects.all().order_by("category")
    serializer_class = UnitsCategoriesSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = ["category"]
    ordering_fields = ["id", "category", "created_at"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)