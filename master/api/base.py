# hr/api/masters/base.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.http import HttpResponse
import csv
import io

class MasterBaseViewSet(viewsets.ModelViewSet):
    """
    Standard Master ViewSet for ERP:
    - CRUD
    - bulk-delete (POST)
    - export (GET)
    - template (GET)
    - import (POST) -> call celery task (optional)
    """

    # override per module
    search_fields = ["name"]
    ordering_fields = ["id", "name"]
    export_fields = ["id", "name"]  # columns exported
    template_headers = ["name"]     # headers template import

    # soft delete optional:
    soft_delete_field = None  # e.g. "is_active" or "is_deleted"

    def perform_soft_delete(self, qs) -> bool:
        field = getattr(self, "soft_delete_field", None)
        if not field:
            return False
        # pastikan field ada
        try:
            qs.model._meta.get_field(field)
        except Exception:
            return False

        # untuk model kamu: is_deleted -> True
        qs.update(**{field: True})
        return True

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])
        hard = bool(request.data.get("hard", False))  # hard delete harus explicit

        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty list"}, status=400)

        qs = self.get_queryset().filter(id__in=ids)

        with transaction.atomic():
            # 1) default: soft delete
            if not hard and self.perform_soft_delete(qs):
                return Response({"deleted": qs.count(), "mode": "soft"}, status=200)

            # 2) hard delete hanya kalau hard=true
            if hard:
                deleted_count, _ = qs.delete()
                return Response({"deleted": deleted_count, "mode": "hard"}, status=200)

            # 3) kalau soft delete tidak dikonfigurasi, jangan hard delete diam-diam
            return Response(
                {
                    "detail": "Soft delete not enabled for this resource. Set soft_delete_field or use hard=true.",
                    "soft_delete_field": getattr(self, "soft_delete_field", None),
                    "viewset": self.__class__.__name__,
                },
                status=400,
            )
        
        # Restore (optional, hanya untuk soft delete dengan field is_deleted)
        @action(detail=False, methods=["post"], url_path="bulk-restore")
        def bulk_restore(self, request):
            ids = request.data.get("ids", [])
            if not isinstance(ids, list) or not ids:
                return Response({"detail": "ids must be a non-empty list"}, status=400)

            field = getattr(self, "soft_delete_field", None)
            if field != "is_deleted":
                return Response({"detail": "bulk-restore only supports is_deleted"}, status=400)

            qs = self.get_queryset().filter(id__in=ids)
            updated = qs.update(is_deleted=False)
            return Response({"restored": updated, "mode": "restore"}, status=200)
    # ---------- EXPORT CSV ----------
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="export.csv"'

        writer = csv.writer(response)
        writer.writerow(self.export_fields)

        for obj in qs:
            row = []
            for f in self.export_fields:
                row.append(getattr(obj, f, ""))
            writer.writerow(row)

        return response

    # ---------- DOWNLOAD TEMPLATE ----------
    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="template.csv"'
        writer = csv.writer(response)
        writer.writerow(self.template_headers)
        return response

    # ---------- IMPORT (UPLOAD FILE) ----------
    def handle_import(self, file, request):
        return Response({"detail": "import not implemented for this master yet"}, status=501)

    @action(detail=False, methods=["post"], url_path="import")
    def import_data(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "file is required"}, status=400)
        return self.handle_import(file, request)
