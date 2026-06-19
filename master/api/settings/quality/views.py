from rest_framework import filters
from core.permissions import GlobalMasterPermission
from geology.models import QualityConfig
from rest_framework.permissions import IsAuthenticated
from .serializers import QualityConfigSerializer
from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet


class QualityConfigViewSet(MasterBaseViewSet):
    queryset = (
        QualityConfig.objects
        .select_related(
            "material",
            "selling_sample_type",
            "monitoring_sample_type",
        )
        .order_by("adjust_sale")
    )

    serializer_class = QualityConfigSerializer
    permission_classes = [IsAuthenticated, GlobalMasterPermission]

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "name",
        "adjust_sale",

        "material__name",

        "selling_sample_type__type_sample",
        "monitoring_sample_type__type_sample",
    ]

    ordering_fields = [
        "id",
        "name",
        "adjust_sale",
        "is_active",
    ]

    ordering = ["adjust_sale"]

    soft_delete_field = None