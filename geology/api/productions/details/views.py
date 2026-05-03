from django.db import connection
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
import os

from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from geology.models import DetailsRoa

from core.permissions import GlobalMasterPermission, RoleReadOnlyForViewer, IUPObjectPermission,user_allowed_iup_ids
from core.pagination import StandardResultsSetPagination
from core.base import BaseViewSet
from .serializers import ProductionsSerializer
from .filters import ProductionsFilter


class ProductionsDetailsViewSet(BaseViewSet):
    queryset = DetailsRoa.objects.all()
    serializer_class = ProductionsSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ProductionsFilter

    search_fields = [
        "tgl_production",
        "sample_number",
        "nama_material",
        "batch_code",
        "iup_code",
        "iup_name",
    ]

    ordering_fields = [
        "id",
        "tgl_production",
        "sample_number",
        "nama_material",
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
        qs = self.queryset.order_by("tgl_production")
        user = self.request.user
        iup_id = self._get_iup_id_param()

        # SYSTEM / SUPERUSER
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        # SITE USER
        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        # MANAGEMENT / GLOBAL VIEWER
        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs
 