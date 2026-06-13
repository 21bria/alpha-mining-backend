from django.db import connection

from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q

from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend


from core.permissions import (
    GlobalMasterPermission, 
    RoleReadOnlyForViewer, 
    IUPObjectPermission,user_allowed_iup_ids
    )

from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet

from geology.models import SamplesDomeView
from master.models import SampleType

from .serializers import SamplesDomeSerializer
from .filters import SamplesFilter

from analytics.models import ExportJob
from analytics.tasks import run_export_job


def get_sample_types(categories=None):
    qs = SampleType.objects.filter(status=1)

    if categories:
        qs = qs.filter(category__in=categories)

    return list(qs.values_list("type_sample", flat=True))


class SamplesDomeViewSet(BaseViewSet):
    queryset = SamplesDomeView.objects.none()
    ordering_fields = ["date_sample"]
    ordering = ["-date_sample"]
    serializer_class = SamplesDomeSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    
    pagination_class = StandardResultsSetPagination
    filter_backends  = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class  = SamplesFilter

    search_fields = [
        "date_sample",
        "sample_id",
        "material",
        "batch",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "date_sample",
        "sample_id",
        "material",
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
        sample_types = get_sample_types(["production", "geology"])

        qs = (
            self.queryset.model.objects
            .filter(type_sample__in=sample_types)
            .order_by("date_sample")
        )

        user = self.request.user
        iup_id = self._get_iup_id_param()

        # SYSTEM / SUPERUSER
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        allowed = user_allowed_iup_ids(user)
        if not allowed:
            return qs.none()

        qs = qs.filter(iup_id__in=allowed)

        # SITE USER
        if getattr(user, "is_site_user", False) and not iup_id:
            iup_id = self._get_active_iup_id_for_user(user)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs
    
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset())

        data = qs.aggregate(
            total_sample=Count("sample_id"),
            total_assay=Count("ni", filter=Q(ni__isnull=False)),
        )

        total_sample = data["total_sample"] or 0
        total_assay = data["total_assay"] or 0

        return Response({
            "total_sample": total_sample,
            "total_assay": total_assay,
            "difference": total_sample - total_assay,
        })
    
    def handle_export(self, request):
        params = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values if len(values) > 1 else request.query_params.get(key)

        job = ExportJob.objects.create(
            module="geology.sample_dome",
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