from uuid import UUID

from django.db import transaction
from django.db import models
from django.http import HttpResponse, FileResponse
from django.conf import settings
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils.dateparse import parse_date
import csv
import os


class BaseViewSet(viewsets.ModelViewSet):
    """
    Standard Master ViewSet for ERP:
    - CRUD
    - bulk-delete
    - bulk-restore
    - export
    - template download
    - import

    Support primary key:
    - UUIDField
    - AutoField / BigAutoField / IntegerField
    """

    search_fields = ["name"]
    ordering_fields = ["id", "name"]

    export_fields = ["id", "name"]
    template_headers = ["name"]

    template_file = None
    soft_delete_field = None

    # ------------------------------
    # PK TYPE DETECTION
    # ------------------------------
    def get_pk_field(self):
        return self.get_queryset().model._meta.pk

    def is_uuid_pk(self) -> bool:
        return isinstance(self.get_pk_field(), models.UUIDField)

    def is_int_pk(self) -> bool:
        return isinstance(
            self.get_pk_field(),
            (
                models.AutoField,
                models.BigAutoField,
                models.IntegerField,
                models.BigIntegerField,
                models.SmallIntegerField,
                models.PositiveIntegerField,
                models.PositiveSmallIntegerField,
            ),
        )

    def normalize_ids(self, ids):
        """
        Validate and normalize incoming ids based on model PK type.
        Return: (valid_ids, invalid_ids)
        """
        valid_ids = []
        invalid_ids = []

        if self.is_uuid_pk():
            for raw_id in ids:
                try:
                    valid_ids.append(str(UUID(str(raw_id).strip())))
                except Exception:
                    invalid_ids.append(raw_id)
            return valid_ids, invalid_ids

        if self.is_int_pk():
            for raw_id in ids:
                try:
                    # hindari bool karena bool subclass int
                    if isinstance(raw_id, bool):
                        raise ValueError("boolean is not valid id")

                    raw_str = str(raw_id).strip()

                    # tolak scientific notation / float / desimal
                    if not raw_str or any(ch in raw_str.lower() for ch in [".", "e"]):
                        raise ValueError("invalid integer id format")

                    valid_ids.append(int(raw_str))
                except Exception:
                    invalid_ids.append(raw_id)
            return valid_ids, invalid_ids

        # fallback generic: string saja
        for raw_id in ids:
            raw_str = str(raw_id).strip()
            if raw_str:
                valid_ids.append(raw_str)
            else:
                invalid_ids.append(raw_id)

        return valid_ids, invalid_ids

    # ------------------------------
    # SOFT DELETE
    # ------------------------------
    def perform_soft_delete(self, qs) -> int:
        field = getattr(self, "soft_delete_field", None)

        if not field:
            return 0

        try:
            qs.model._meta.get_field(field)
        except Exception:
            return 0

        return qs.update(**{field: True})

    # ------------------------------
    # SOFT RESTORE
    # ------------------------------
    def perform_soft_restore(self, qs) -> int:
        field = getattr(self, "soft_delete_field", None)

        if field != "is_deleted":
            return 0

        try:
            qs.model._meta.get_field(field)
        except Exception:
            return 0

        return qs.update(**{field: False})

    # ------------------------------
    # BULK DELETE
    # ------------------------------
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])
        hard = bool(request.data.get("hard", False))

        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_ids, invalid_ids = self.normalize_ids(ids)

        if invalid_ids:
            return Response(
                {
                    "detail": "Some ids are invalid",
                    "invalid_ids": invalid_ids,
                    "expected_pk_type": self.get_pk_field().__class__.__name__,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        pk_name = self.get_queryset().model._meta.pk.name
        qs = self.get_queryset().filter(**{f"{pk_name}__in": valid_ids})

        with transaction.atomic():
            if not hard:
                updated = self.perform_soft_delete(qs)
                if updated:
                    return Response(
                        {"deleted": updated, "mode": "soft"},
                        status=status.HTTP_200_OK,
                    )

            if hard:
                deleted_count, _ = qs.delete()
                return Response(
                    {"deleted": deleted_count, "mode": "hard"},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "detail": "Soft delete not enabled. Set soft_delete_field or use hard=true.",
                    "viewset": self.__class__.__name__,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ------------------------------
    # BULK RESTORE
    # ------------------------------
    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_ids, invalid_ids = self.normalize_ids(ids)

        if invalid_ids:
            return Response(
                {
                    "detail": "Some ids are invalid",
                    "invalid_ids": invalid_ids,
                    "expected_pk_type": self.get_pk_field().__class__.__name__,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = 0
        pk_name = self.get_queryset().model._meta.pk.name
        qs = self.get_queryset().filter(**{f"{pk_name}__in": valid_ids})

        with transaction.atomic():
            updated = self.perform_soft_restore(qs)

        if not updated:
            return Response(
                {"detail": "bulk-restore only supports soft_delete_field='is_deleted'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"restored": updated}, status=status.HTTP_200_OK)
    
    # ------------------------------
    # BULK CREATE
    # ------------------------------
    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response(
                {"detail": "Payload must be a list of objects"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not data:
            return Response(
                {"detail": "Payload is empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instances = serializer.save()

        return Response(
            {
                "detail": "Bulk create success",
                "count": len(instances),
            },
            status=status.HTTP_201_CREATED,
        )
    
    # ------------------------------
    # RANGE DELETE HELPERS
    # ------------------------------
    range_delete_field = None
    range_delete_iup_field = None

    def get_range_delete_field(self):
        field = getattr(self, "range_delete_field", None)
        if not field:
            return None

        try:
            self.get_queryset().model._meta.get_field(field)
            return field
        except Exception:
            return None

    def get_range_delete_iup_field(self):
        field = getattr(self, "range_delete_iup_field", None)
        if not field:
            return None

        try:
            self.get_queryset().model._meta.get_field(field)
            return field
        except Exception:
            return None

    def apply_range_delete_iup_filter(self, qs, iup):
        field = self.get_range_delete_iup_field()
        if not field or not iup:
            return qs
        return qs.filter(**{field: iup})

    def get_range_delete_queryset(self, request, start_date, end_date):
        field = self.get_range_delete_field()
        if not field:
            return None, Response(
                {"detail": "range_delete_field is not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not start_date or not end_date:
            return None, Response(
                {"detail": "date_start and date_end are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = parse_date(str(start_date))
        end = parse_date(str(end_date))

        if not start or not end:
            return None, Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start > end:
            return None, Response(
                {"detail": "date_start cannot be greater than date_end"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.filter_queryset(self.get_queryset()).filter(
            **{
                f"{field}__gte": start,
                f"{field}__lte": end,
            }
        )

        return qs, None
    
    # ------------------------------
    # RANGE DELETE PREVIEW
    # ------------------------------
    @action(detail=False, methods=["post"], url_path="delete-range/preview")
    def delete_range_preview(self, request):
        date_start = request.data.get("date_start")
        date_end = request.data.get("date_end")
        iup = request.data.get("iup")

        qs, error = self.get_range_delete_queryset(request, date_start, date_end)
        if error:
            return error

        qs = self.apply_range_delete_iup_filter(qs, iup)

        return Response(
            {
                "count": qs.count(),
                "mode": "soft" if self.soft_delete_field else "hard",
                "iup": iup,
            },
            status=status.HTTP_200_OK,
        )
    
    # ------------------------------
    # RANGE DELETE
    # ------------------------------
    @action(detail=False, methods=["post"], url_path="delete-range")
    def delete_range(self, request):
        date_start = request.data.get("date_start")
        date_end = request.data.get("date_end")
        hard = bool(request.data.get("hard", False))
        iup = request.data.get("iup")

        qs, error = self.get_range_delete_queryset(request, date_start, date_end)
        if error:
            return error

        qs = self.apply_range_delete_iup_filter(qs, iup)

        total = qs.count()
        if total == 0:
            return Response(
                {"deleted": 0, "detail": "No data found in selected range"},
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            if hard:
                deleted_count, _ = qs.delete()
                return Response(
                    {
                        "deleted": deleted_count,
                        "mode": "hard",
                        "date_start": date_start,
                        "date_end": date_end,
                        "iup": iup,
                    },
                    status=status.HTTP_200_OK,
                )

            updated = self.perform_soft_delete(qs)
            return Response(
                {
                    "deleted": updated,
                    "mode": "soft",
                    "date_start": date_start,
                    "date_end": date_end,
                    "iup": iup,
                },
                status=status.HTTP_200_OK,
            )

    # ------------------------------
    # EXPORT CSV
    # ------------------------------
    # @action(detail=False, methods=["get"], url_path="export")
    # def export(self, request):
        qs = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        writer = csv.writer(response)
        writer.writerow(self.export_fields)

        for obj in qs:
            row = []

            for f in self.export_fields:
                if "__" in f:
                    value = obj
                    for part in f.split("__"):
                        value = getattr(value, part, "")
                        if value is None:
                            break
                else:
                    value = getattr(obj, f, "")

                row.append(value)

            writer.writerow(row)

        return response
   
      
    # ------------------------------
    # EXPORT HANDLER (OVERRIDE POINT)
    # ------------------------------
    def handle_export(self, request):
        return Response(
            {"detail": "export not implemented for this module"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
    
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """
        Smart Export:
        - If child overrides handle_export → use it (Celery / custom)
        - Else:
            - small data → direct CSV
            - large data → auto Celery (optional)
        """
        custom_handler = getattr(self, "handle_export", None)

        if callable(custom_handler):
            base_handler = getattr(BaseViewSet, "handle_export", None)
            if getattr(custom_handler, "__func__", None) is not getattr(base_handler, "__func__", None):
                return custom_handler(request)

        qs = self.filter_queryset(self.get_queryset())

        # AUTO SWITCH (optional)
        count = qs.count()
        if count > 10000:
            return Response(
                {
                    "detail": "Data too large, use async export",
                    "count": count
                },
                status=400
            )

        # fallback CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        writer = csv.writer(response)
        writer.writerow(self.export_fields)

        for obj in qs.iterator(chunk_size=2000):
            row = []

            for f in self.export_fields:
                if "__" in f:
                    value = obj
                    for part in f.split("__"):
                        value = getattr(value, part, "")
                        if value is None:
                            break
                else:
                    value = getattr(obj, f, "")

                row.append(value)

            writer.writerow(row)

        return response

    # ------------------------------
    # TEMPLATE DOWNLOAD
    # ------------------------------
    def get_template_file(self):
        return None

    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request):
        try:
            file_path = self.get_template_file()

            print("VIEWSET:", self.__class__.__name__)
            print("TEMPLATE FILE:", file_path)

            if not file_path:
                return Response(
                    {"detail": "Template file is not configured"},
                    status=400,
                )

            full_path = os.path.join(settings.BASE_DIR, file_path)

            print("FULL PATH:", full_path)
            print("EXISTS:", os.path.exists(full_path))

            if not os.path.exists(full_path):
                return Response(
                    {"detail": f"Template file not found: {full_path}"},
                    status=404,
                )

            return FileResponse(
                open(full_path, "rb"),
                as_attachment=True,
                filename=os.path.basename(full_path),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            print("TEMPLATE ERROR:", repr(e))
            return Response(
                {"detail": str(e)},
                status=500,
            )

    # ------------------------------
    # IMPORT
    # ------------------------------
    def handle_import(self, file, request):
        return Response(
            {"detail": "import not implemented for this module"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=False, methods=["post"], url_path="import")
    def import_data(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"detail": "file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self.handle_import(file, request)