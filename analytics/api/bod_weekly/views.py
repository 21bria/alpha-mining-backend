from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet

from analytics.models_bod_weekly import BodWeeklyReport,BodWeeklyDocument
from .serializers import BodWeeklyReportSerializer,BodWeeklyDocumentSerializer
from .filters import WeeklyFilter

from master.api.base import MasterBaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
)

class WeeklyReportViewSet(MasterBaseViewSet):
    queryset = (
        BodWeeklyReport.objects
        .select_related("iup", "user")
        .prefetch_related(
            "mining_rows",
            "metrics",
            "manpower_rows",
            "documents",
        )
        .all()
        .order_by("-year", "-week", "-created_at")
    )

    serializer_class = BodWeeklyReportSerializer

    # publik untuk semua user login
    permission_classes = [IsAuthenticated]

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]

    filterset_class = WeeklyFilter

    search_fields = [
        "report_code",
        "title",
        "remarks",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "year",
        "week",
        "period_start",
        "period_end",
        "status",
        "created_at",
        "updated_at",
    ]

class BodWeeklyReportViewSet(MasterBaseViewSet):
    queryset = (
        BodWeeklyReport.objects
        .select_related("iup", "user")
        .prefetch_related(
            "mining_rows",
            "metrics",
            "manpower_rows",
            "documents",
        )
        .all()
        .order_by("-year", "-week", "-created_at")
    )

    serializer_class = BodWeeklyReportSerializer

    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends  = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]

    filterset_class  = WeeklyFilter
    search_fields = [
        "report_code",
        "title",
        "remarks",
        "iup__iup_code",
        "iup__iup_name",
        "user__username",
    ]

    ordering_fields = [
        "id",
        "year",
        "week",
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

class BodWeeklyDocumentViewSet(ModelViewSet):
    queryset = BodWeeklyDocument.objects.all()
    serializer_class = BodWeeklyDocumentSerializer
    permission_classes = [IsAuthenticated]

# class BodWeeklyDocumentViewSet(ModelViewSet):
#     queryset = (
#         BodWeeklyDocument.objects
#         .select_related("report", "report__iup")
#         .all()
#     )
#     serializer_class = BodWeeklyDocumentSerializer

#     permission_classes = [
#         IsAuthenticated,
#         RoleReadOnlyForViewer,
#         GlobalMasterPermission,
#     ]

#     def get_queryset(self):
#         qs = super().get_queryset()
#         user = self.request.user

#         if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
#             return qs

#         allowed_iup_ids = getattr(user, "allowed_iup_ids", None)
#         if callable(allowed_iup_ids):
#             allowed_iup_ids = allowed_iup_ids()

#         if not allowed_iup_ids:
#             from core.permissions import user_allowed_iup_ids
#             allowed_iup_ids = user_allowed_iup_ids(user)

#         return qs.filter(report__iup_id__in=allowed_iup_ids)