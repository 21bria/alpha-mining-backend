from django.db import connection
from django.http import FileResponse
from django.conf import settings
import os
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from geology.models import Waybills,listWaybills,listTemporary
from geology.models.geology_sample_production import SampleProductions
from geology.models.geology_waybills_temp import WaybillsTemporary
from geology.services.generate_waybill_number import generate_number
from imports.models import ImportJob
from imports.tasks.master_imports import run_import_job

from core.permissions import (
    GlobalMasterPermission, 
    RoleReadOnlyForViewer, 
    IUPObjectPermission,
    user_allowed_iup_ids
    )
from .serializers import WaybillsSerializer,WaybillsCRUDSerializer
from master.api.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from .filters import WaybillFilter

# export
from analytics.models import ExportJob
from analytics.tasks import run_export_job

class WaybillsViewSet(BaseViewSet):
    queryset = listWaybills.objects.all()

    ordering_fields = ["tgl_deliver"]
    ordering = ["-tgl_deliver"]

    serializer_class = WaybillsSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = WaybillFilter

    # search pakai field yang benar
    search_fields = [
        "waybill_number",
        "tgl_deliver",
        "sample_id",
        "sample_status",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "waybill_number",
        "tgl_deliver",
        "sample_id",
        "sample_status"
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
        qs = self.queryset
        user = self.request.user
        iup_id = self._get_iup_id_param()

        if getattr(user, "is_superuser", False) or getattr(user, "role", None) == "SYSTEM":
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        if getattr(user, "role", None) == "SITE" and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

class WaybillsViewCRUDSet(BaseViewSet):
    queryset = Waybills.objects.select_related("iup").all().order_by("tgl_deliver")
    serializer_class = WaybillsCRUDSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination

    search_fields = [
        "waybill_number",
        "tgl_deliver",
        "sample_id",
        "iup__iup_code",
        "iup__iup_name",
    ]

    ordering_fields = [
        "id",
        "waybill_number",
        "tgl_deliver",
        "sample_id",
    ]

    export_fields = [
        "id",
        "iup_code",
        "iup_name",
        "tgl_deliver",
        "waybill_number",
        "sample_id",
    ]

    soft_delete_field = "is_deleted"
    range_delete_field = "tgl_deliver"
    range_delete_iup_field = "iup_id"
    
    def get_queryset(self):
        return Waybills.objects.filter(is_deleted=False)

    def handle_import(self, file, request):
        job = ImportJob.objects.create(
            module="geology.waybills",
            file=file,
            created_by=request.user if request.user.is_authenticated else None,
            status="pending",
            progress=0,
        )

        schema_name = connection.schema_name
        run_import_job.delay(schema_name, str(job.id))

        return Response({"status": "import queued", "job_id": str(job.id)}, status=202)

    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="geology.waybills",
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
            "geology_waybills_import_template.xlsx",
        )

        if not os.path.exists(file_path):
            return Response(
                {"detail": f"Template file not found: {file_path}"},
                status=404,
            )

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="geology_waybills_import_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    
    @action(detail=False, methods=["post"], url_path="add-range")
    def add_range(self, request):
        sample_from = request.data.get("from")
        sample_to = request.data.get("to")
        iup_id = request.data.get("iup") or request.data.get("iup_id")

        if not sample_from or not sample_to:
            return Response(
                {"detail": "from and to are required"},
                status=400,
            )

        sample_qs = (
            SampleProductions.objects
            .filter(
                is_deleted=False,
                sample_number__gte=sample_from,
                sample_number__lte=sample_to,
            )
            .order_by("sample_number")
        )

        if iup_id:
            sample_qs = sample_qs.filter(iup_id=iup_id)

        sample_numbers = list(sample_qs.values_list("sample_number", flat=True))

        existing_waybill = set(
            Waybills.objects
            .filter(sample_id__in=sample_numbers)
            .values_list("sample_id", flat=True)
        )

        existing_temp = set(
            WaybillsTemporary.objects
            .filter(
                user=request.user,
                sample_id__in=sample_numbers,
            )
            .values_list("sample_id", flat=True)
        )

        inserts = []
        duplicate_waybill_samples = []
        duplicate_temp_samples = []

        for obj in sample_qs:
            if obj.sample_number in existing_waybill:
                duplicate_waybill_samples.append(obj.sample_number)
                continue

            if obj.sample_number in existing_temp:
                duplicate_temp_samples.append(obj.sample_number)
                continue

            inserts.append(
                WaybillsTemporary(
                    iup_id=obj.iup_id,
                    code=f"TEMP-{obj.iup_id}-{obj.sample_number}",
                    sample_id=obj.sample_number,
                    id_type_sample=obj.id_type_sample,
                    id_method=obj.id_method,
                    id_material=obj.id_material,
                    sampling_area=obj.sampling_area or obj.discharge_area,
                    sampling_point=obj.sampling_point or obj.product_code,
                    batch_code=obj.batch_code or "",
                    status_input="TEMP",
                    no_save="",
                    user=request.user,
                )
            )

        if inserts:
            WaybillsTemporary.objects.bulk_create(inserts)

        return Response(
            {
                "success": True,
                "found": len(sample_numbers),
                "inserted": len(inserts),
                "duplicate_waybill": len(duplicate_waybill_samples),
                "duplicate_waybill_samples": duplicate_waybill_samples,
                "duplicate_temp": len(duplicate_temp_samples),
                "duplicate_temp_samples": duplicate_temp_samples,
            },
            status=200,
        )
    
    # ambil data sementara untuk ditampilkan di frontend sebelum disimpan permanen
    @action(detail=False, methods=["get"], url_path="temporary")
    def temporary(self, request):
        qs = (
            listTemporary.objects
            .filter(user_id=request.user.id)
            .order_by("sample_id")
        )

        data = list(qs.values(
            "sample_id",
            "type_sample",
            "sample_method",
            "material",
            "sampling_area",
            "sampling_point",
            "batch_code",
            "status_input",
        ))

        return Response(data)
    
    @action(detail=False, methods=["post"], url_path="cancel-temp")
    def cancel_temp(self, request):

        sample_id = request.data.get("sample_id")

        if not sample_id:
            return Response(
                {"detail": "sample_id is required"},
                status=400,
            )

        updated = (
            WaybillsTemporary.objects
            .filter(
                user=request.user,
                sample_id=sample_id,
                status_input="TEMP",
            )
            .update(status_input="CANCEL")
        )

        return Response({
            "success": True,
            "updated": updated,
        })
    
    @action(detail=False, methods=["post"], url_path="clear-temp")
    def clear_temp(self, request):

        deleted_count, _ = (
            WaybillsTemporary.objects
            .filter(
                user=request.user,
                # status_input="TEMP",
            )
            .delete()
        )

        return Response({
            "success": True,
            "deleted": deleted_count,
        })
    
    @action(detail=False, methods=["get"], url_path="number")
    def number(self, request):

        date_delivery = request.query_params.get("date_delivery")

        if not date_delivery:
            return Response(
                {"detail": "date_delivery is required"},
                status=400,
            )

        new_number = generate_number(date_delivery)

        return Response({
            "new_number": new_number
        })
    
    @action(detail=False, methods=["post"], url_path="submit-temp")
    def submit_temp(self, request):
        tgl_deliver = request.data.get("tgl_deliver")
        delivery_time = request.data.get("delivery_time")
        waybill_number = request.data.get("waybill_number")
        mral_order = request.data.get("mral_order", "NO")
        roa_order = request.data.get("roa_order", "NO")
        remarks = request.data.get("remarks")
        iup_id = request.data.get("iup") or request.data.get("iup_id")

        if not tgl_deliver:
            return Response({"detail": "tgl_deliver is required"}, status=400)

        if not delivery_time:
            return Response({"detail": "delivery_time is required"}, status=400)

        if not waybill_number:
            return Response({"detail": "waybill_number is required"}, status=400)

        temp_qs = (
            WaybillsTemporary.objects
            .select_related("iup")
            .filter(user=request.user, status_input="TEMP")
            .order_by("sample_id")
        )

        if iup_id:
            temp_qs = temp_qs.filter(iup_id=iup_id)

        temp_rows = list(temp_qs)

        if not temp_rows:
            return Response(
                {"detail": "No temporary samples found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_ids = [row.sample_id for row in temp_rows]

        existing = set(
            Waybills.objects
            .filter(
                iup_id__in=[row.iup_id for row in temp_rows],
                sample_id__in=sample_ids,
            )
            .values_list("iup_id", "sample_id")
        )

        inserts = []

        for row in temp_rows:
            if (row.iup_id, row.sample_id) in existing:
                continue

            date_part = str(tgl_deliver).replace("-", "")
            iup_code = row.iup.iup_code if row.iup_id and row.iup else f"IUP-{row.iup_id}"
            code = f"{iup_code}-{date_part}-{row.sample_id}"

            inserts.append(
                Waybills(
                    iup_id=row.iup_id,
                    code=code,
                    tgl_deliver=tgl_deliver,
                    delivery_time=delivery_time,
                    waybill_number=waybill_number,
                    qty=len(temp_rows),
                    sample_id=row.sample_id,
                    mral_order=mral_order,
                    roa_order=roa_order,
                    delivery=f"{tgl_deliver} {delivery_time}",
                    remarks=remarks,
                    user=request.user,
                )
            )

        if not inserts:
            return Response(
                {
                    "detail": "All temporary samples already exist in Waybill",
                    "duplicate": len(existing),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            Waybills.objects.bulk_create(inserts)

            temp_qs.update(
                status_input="SAVE",
                no_save="SAVE",
            )

        return Response(
            {
                "success": True,
                "waybill_number": waybill_number,
                "inserted": len(inserts),
                "duplicate": len(existing),
            },
            status=status.HTTP_201_CREATED,
        )
    
    @action(detail=False, methods=["post"], url_path="clear-saved-temp")
    def clear_saved_temp(self, request):
        deleted_count, _ = (
            WaybillsTemporary.objects
            .filter(
                user=request.user,
                status_input="SAVE",
            )
            .delete()
        )

        return Response({
            "success": True,
            "deleted": deleted_count,
        })
