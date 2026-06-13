from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from analytics.models_report_management import (
    ReportManagement,
    ReportManagementDocument,
)

from .serializers import (
    ReportManagementSerializer,
    ReportManagementDocumentSerializer,
)

from .filters import ReportManagementFilter

from analytics.services.report_management_sync import sync_report_management
from analytics.services.report_management_live import build_live_management_report

from master.api.base import MasterBaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
)

def normalize_week(value):
    if not value:
        return None

    value = str(value)

    # support format: 2026-20
    if "-" in value:
        value = value.split("-")[-1]

    return int(value)
from datetime import date, timedelta
import calendar


def get_week_range(year, week):
    start = date.fromisocalendar(int(year), int(week), 1)
    end = start + timedelta(days=6)

    return start.isoformat(), end.isoformat()


def get_month_range(year, month):
    last_day = calendar.monthrange(int(year), int(month))[1]

    return (
        date(int(year), int(month), 1).isoformat(),
        date(int(year), int(month), last_day).isoformat(),
    )

class ManagementReportViewSet(MasterBaseViewSet):
    queryset = (
        ReportManagement.objects
        .select_related("iup", "user")
        .prefetch_related(
            "mining_rows",
            "metrics",
            "manpower_rows",
            "documents",
        )
        .all()
        .order_by("-period_start", "-created_at")
    )

    serializer_class = ReportManagementSerializer

    # public internal: semua user login bisa lihat
    permission_classes = [IsAuthenticated]

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]

    filterset_class = ReportManagementFilter

    search_fields = [
        "report_code",
        "period_key",
        "title",
        "remarks",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "period_type",
        "period_key",
        "yearly",
        "monthly",
        "weekly",
        "period_start",
        "period_end",
        "status",
        "created_at",
        "updated_at",
    ]

    @action(detail=False, methods=["get"], url_path="view")
    def view_report(self, request):
        period_type = (
            request.GET.get("period_type")
            or request.GET.get("filter_type")
            or "weekly"
        ).lower()

        iup_id = request.GET.get("iup_id")

        year = request.GET.get("year") or request.GET.get("yearly")
        month = request.GET.get("month") or request.GET.get("monthly")
        week = request.GET.get("week") or request.GET.get("weekly")
        week = normalize_week(week)

        period_start = (request.GET.get("period_start")or request.GET.get("date_start"))
        period_end = (request.GET.get("period_end")or request.GET.get("date_end"))
        
        # AUTO GENERATE RANGE
        if period_type == "weekly" and year and week and not period_start:
            period_start, period_end = get_week_range(year, week)

        elif period_type == "monthly" and year and month and not period_start:
            period_start, period_end = get_month_range(year, month)

        elif period_type == "yearly" and year and not period_start:
            period_start = f"{year}-01-01"
            period_end = f"{year}-12-31"


        report = None

        # range selalu live preview
        if period_type != "range":
            qs = self.get_queryset().filter(
                iup_id=iup_id,
                period_type=period_type,
                is_deleted=False,
            )

            if period_type == "weekly":
                qs = qs.filter(year=year, week=week)

            elif period_type == "monthly":
                qs = qs.filter(year=year, month=month)

            elif period_type == "yearly":
                qs = qs.filter(year=year)

            else:
                qs = qs.none()

            report = qs.first()

        if report:
            serializer = self.get_serializer(report)

            return Response({
                "mode": "report",
                "status": report.status,
                "data": serializer.data,
            })

        live_data = build_live_management_report(
            iup_id=iup_id,
            period_type=period_type,
            year=year,
            month=month,
            week=week,
            period_start=period_start,
            period_end=period_end,
        )

        return Response({
            "mode": "live",
            "status": "Live",
            "data": live_data,
        })
 

class ReportManagementViewSet(MasterBaseViewSet):
    queryset = (
        ReportManagement.objects
        .select_related("iup", "user")
        .prefetch_related(
            "mining_rows",
            "metrics",
            "manpower_rows",
            "documents",
        )
        .all()
        .order_by("-period_start", "-created_at")
    )

    serializer_class = ReportManagementSerializer

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

    filterset_class = ReportManagementFilter

    search_fields = [
        "report_code",
        "period_key",
        "title",
        "remarks",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "period_type",
        "period_key",
        "yearly",
        "monthly",
        "weekly",
        "period_start",
        "period_end",
        "status",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed_iup_ids = getattr(user, "allowed_iup_ids", None)

        if callable(allowed_iup_ids):
            allowed_iup_ids = allowed_iup_ids()

        if not allowed_iup_ids:
            from core.permissions import user_allowed_iup_ids
            allowed_iup_ids = user_allowed_iup_ids(user)

        return qs.filter(iup_id__in=allowed_iup_ids)
    
    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, pk=None):
        report = self.get_object()

        if report.status != "Draft":
            raise ValidationError("Only draft report can be synchronized.")

        sync_report_management(report, request.user)

        serializer = self.get_serializer(report)

        return Response({
            "success": True,
            "message": "Report synchronized successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        report = self.get_object()

        if report.status != "Draft":
            raise ValidationError("Only draft report can be published.")

        sync_report_management(report, request.user)

        report.status = "Published"
        report.published_at = timezone.now()
        report.published_by = request.user
        report.save(update_fields=[
            "status",
            "published_at",
            "published_by",
            "updated_at",
        ])

        serializer = self.get_serializer(report)

        return Response({
            "success": True,
            "message": "Report published successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)


class ReportManagementDocumentViewSet(ModelViewSet):
    queryset = (
        ReportManagementDocument.objects
        .select_related("report", "report__iup", "user")
        .all()
        .order_by("-document_date", "-id")
    )

    serializer_class = ReportManagementDocumentSerializer
    permission_classes = [IsAuthenticated]