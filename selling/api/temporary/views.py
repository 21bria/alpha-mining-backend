from django.db import connection
from rest_framework.response import Response
from rest_framework import filters, status
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticated

from core.permissions import (
    GlobalMasterPermission,
    RoleReadOnlyForViewer,
    IUPObjectPermission,
    user_allowed_iup_ids,
)
from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet

from selling.models import (
    SellingBargingTemporaryView,
    SellingBargingTemporary,
)

from .serializers import (
    SellingBargingTemporarySerializer,
    SellingBargingTemporaryWriteSerializer,
    SellingBargingTemporaryDetailSerializer
)
from .filters import SellingFilter

from analytics.models import ExportJob
from analytics.tasks import run_export_job

class SellingTemporaryViewSet(BaseViewSet):
    queryset = SellingBargingTemporaryView.objects.none()
    serializer_class = SellingBargingTemporarySerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = SellingFilter

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
        "material",
    ]
    ordering = ["date_hauling"]

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
        qs = self.queryset.model.objects.order_by("date_hauling")

        user = self.request.user
        iup_id = self._get_iup_id_param()

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
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

class SellingBargingTemporaryCRUDViewSet(BaseViewSet):
    queryset = SellingBargingTemporary.objects.all().order_by("-created_at")

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = {
        "iup_id": ["exact"],
        "date_hauling": ["exact", "gte", "lte"],
        "created_at": ["exact", "gte", "lte"],
        "user__username": ["exact", "icontains"],
        "barge_code": ["exact"],
        "code_lot": ["exact", "icontains"],
        "code_inc": ["exact", "icontains"],
        "code_sub": ["exact", "icontains"],
        "unit_code": ["exact", "icontains"],
        "shift": ["exact", "icontains"],
        "id_material": ["exact"],
        "id_pile": ["exact"],
    }

    search_fields = [
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
        "code_lot",
        "unit_code",
        "code_inc",
        "code_sub",
    ]

    ordering_fields = [
        "id",
        "created_at",
        "date_hauling",
        "time_hauling",
        "code_lot",
        "unit_code",
        "iup__iup_code",
        "iup__iup_name",
    ]
    ordering = ["-created_at"]

    soft_delete_field = "is_deleted"
    range_delete_field = "date_production"
    range_delete_iup_field = "iup_id"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return SellingBargingTemporaryWriteSerializer
        if self.action == "retrieve":
            return SellingBargingTemporaryDetailSerializer
        return SellingBargingTemporarySerializer

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
        qs = super().get_queryset().select_related("iup", "user")

        user = self.request.user
        iup_id = self._get_iup_id_param()

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
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

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="selling.barging_temporary",
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