from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from django.db import models

from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from selling.models import SellingBargingAdjustment,SellingBarging
from mining.models import mineProductions
from geology.models import OreProductions
from master.models import SellingCode
from .serializers import SellingBargingAdjustmentSerializer

from master.api.base import MasterBaseViewSet
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    RoleReadOnlyForViewer,
    GlobalMasterPermission,
    IUPObjectPermission,
    user_allowed_iup_ids,
)


class SellingBargingAdjustmentViewSet(MasterBaseViewSet):
    queryset = (
        SellingBargingAdjustment.objects
        .select_related("code_lot", "user", "code_lot__iup")
        .all()
        .order_by("-created_at")
    )
    serializer_class = SellingBargingAdjustmentSerializer
    permission_classes = [
        IsAuthenticated,
        RoleReadOnlyForViewer,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = [
        "code_lot",
        "status",
        "date_arrival",
        "date_departure",
        "code_lot__iup_id",
        "code_lot__type",
    ]

    search_fields = [
        "code_lot__code",
        "code_lot__description",
        "code_lot__type",
        "description",
        "user__username",
        "status",
        "jetty_departure",
    ]

    ordering_fields = [
        "id",
        "date_arrival",
        "date_departure",
        "ritase_ori",
        "tonnage_ori",
        "tonnage_adjust",
        "status",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        iup_id = self.request.query_params.get("iup_id")
        type_param = self.request.query_params.get("type")

        if iup_id:
            qs = qs.filter(code_lot__iup_id=iup_id)

        if type_param:
            qs = qs.filter(code_lot__type__iexact=type_param)

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs

        allowed_iup_ids = getattr(user, "allowed_iup_ids", None)
        if callable(allowed_iup_ids):
            allowed_iup_ids = allowed_iup_ids()

        if not allowed_iup_ids:
            allowed_iup_ids = user_allowed_iup_ids(user)

        return qs.filter(code_lot__iup_id__in=allowed_iup_ids)
    
    @action(detail=False, methods=["get"], url_path="totals-by-code-lot")
    def totals_by_code_lot(self, request):
        code_lot_id = request.query_params.get("code_lot_id")

        if not code_lot_id:
            return Response(
                {"detail": "code_lot_id wajib diisi"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code_lot_obj = SellingCode.objects.filter(id=code_lot_id).first()

        if not code_lot_obj:
            return Response(
                {"detail": "Code lot tidak ditemukan"},
                status=status.HTTP_404_NOT_FOUND,
            )

        code_lot_code = code_lot_obj.code
        iup_id = request.query_params.get("iup_id")
        user = request.user

        allowed_iup_ids = None
        if not (getattr(user, "is_system", False) or getattr(user, "is_superuser", False)):
            allowed_iup_ids = getattr(user, "allowed_iup_ids", None)

            if callable(allowed_iup_ids):
                allowed_iup_ids = allowed_iup_ids()

            if not allowed_iup_ids:
                allowed_iup_ids = user_allowed_iup_ids(user)

        # =========================
        # BARGING
        # =========================
        barging_qs = SellingBarging.objects.filter(
            code_lot__iexact=code_lot_code
        )

        if iup_id:
            barging_qs = barging_qs.filter(iup_id=iup_id)

        if allowed_iup_ids is not None:
            barging_qs = barging_qs.filter(iup_id__in=allowed_iup_ids)

        barging_total = barging_qs.aggregate(
            total_count=Count("id"),
            total_tonnage=Sum("tonnage"),
            total_ritase=Sum("ritase_group"),
            direct_count=Count("id", filter=models.Q(direct__iexact="Yes")),
            direct_tonnage=Sum("tonnage", filter=models.Q(direct__iexact="Yes")),
            direct_ritase=Sum("ritase_group", filter=models.Q(direct__iexact="Yes")),
        )

        total_barging_count = int(barging_total["total_count"] or 0)
        total_barging_tonnage = Decimal(str(barging_total["total_tonnage"] or 0))
        total_barging_ritase = int(barging_total["total_ritase"] or 0)

        direct_barging_count = int(barging_total["direct_count"] or 0)
        direct_barging_tonnage = Decimal(str(barging_total["direct_tonnage"] or 0))
        direct_barging_ritase = int(barging_total["direct_ritase"] or 0)

        # =========================
        # AMBIL ID PILE DARI BARGING
        # =========================
        barging_ref = (
            barging_qs
            .exclude(id_pile__isnull=True)
            .first()
        )

        id_pile = barging_ref.id_pile if barging_ref else None

        # mining kamu sebelumnya pakai dome_id,
        # untuk sementara mapping-nya dari id_pile barging
        dome_id = id_pile

        # =========================
        # GEOLOGY
        # =========================
        if id_pile:
            geology_qs = OreProductions.objects.filter(
                id_pile=id_pile,
                direct__iexact="Yes",
            )
        else:
            geology_qs = OreProductions.objects.none()

        if iup_id:
            geology_qs = geology_qs.filter(iup_id=iup_id)

        if allowed_iup_ids is not None:
            geology_qs = geology_qs.filter(iup_id__in=allowed_iup_ids)

        geology_total = geology_qs.aggregate(
            count=Count("id"),
            tonnage=Sum("tonnage"),
            ritase=Sum("ritase"),
        )

        direct_geology_count = int(geology_total["count"] or 0)
        direct_geology_tonnage = Decimal(str(geology_total["tonnage"] or 0))
        direct_geology_ritase = int(geology_total["ritase"] or 0)

        # =========================
        # MINING
        # =========================
        if dome_id:
            mining_qs = mineProductions.objects.filter(
                dome_id=dome_id,
                direct__iexact="Yes",
            )
        else:
            mining_qs = mineProductions.objects.none()

        if iup_id:
            mining_qs = mining_qs.filter(iup_id=iup_id)

        if allowed_iup_ids is not None:
            mining_qs = mining_qs.filter(iup_id__in=allowed_iup_ids)

        mining_total = mining_qs.aggregate(
            count=Count("id"),
            tonnage=Sum("tonnage"),
            ritase=Sum("ritase"),
        )

        direct_mining_count = int(mining_total["count"] or 0)
        direct_mining_tonnage = Decimal(str(mining_total["tonnage"] or 0))
        direct_mining_ritase = int(mining_total["ritase"] or 0)

        # =========================
        # GRAND TOTAL DIRECT
        # =========================
        direct_total_count = (
            direct_barging_count
            + direct_mining_count
            + direct_geology_count
        )

        direct_total_tonnage = (
            direct_barging_tonnage
            + direct_mining_tonnage
            + direct_geology_tonnage
        )

        direct_total_ritase = (
            direct_barging_ritase
            + direct_mining_ritase
            + direct_geology_ritase
        )

        return Response({
            "code_lot_id": int(code_lot_id),
            "code_lot": code_lot_code,
            "id_pile": id_pile,
            "dome_id": dome_id,

            "total_barging": {
                "count": total_barging_count,
                "tonnage": total_barging_tonnage,
                "ritase": total_barging_ritase,
            },

            "direct_barging": {
                "count": direct_barging_count,
                "tonnage": direct_barging_tonnage,
                "ritase": direct_barging_ritase,
            },

            "direct_mining": {
                "count": direct_mining_count,
                "tonnage": direct_mining_tonnage,
                "ritase": direct_mining_ritase,
            },

            "direct_geology": {
                "count": direct_geology_count,
                "tonnage": direct_geology_tonnage,
                "ritase": direct_geology_ritase,
            },

            "direct_total": {
                "count": direct_total_count,
                "tonnage": direct_total_tonnage,
                "ritase": direct_total_ritase,
            },
        })