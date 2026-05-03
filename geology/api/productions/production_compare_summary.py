from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import GlobalMasterPermission, IUPObjectPermission, user_allowed_iup_ids
from geology.models import OreProductionsView, DetailsRoa, DetailsMral
from geology.services.production_summary import apply_common_filters, sum_tonnage

class ProductionCompareSummaryView(APIView):
    permission_classes = [
        IsAuthenticated,
        GlobalMasterPermission,
        IUPObjectPermission,
    ]

    def _get_iup_id_param(self, request):
        return request.query_params.get("iup_id") or request.query_params.get("iup")

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

    def apply_iup_scope(self, qs, request):
        user = request.user
        iup_id = self._get_iup_id_param(request)

        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return qs.filter(iup_id=iup_id) if iup_id else qs

        if getattr(user, "is_site_user", False):
            if not iup_id:
                iup_id = self._get_active_iup_id_for_user(user)
            if not iup_id:
                return qs.none()
            return qs.filter(iup_id=iup_id)

        if iup_id:
            qs = qs.filter(iup_id=iup_id)

        return qs

    def get(self, request, *args, **kwargs):
        prod_qs = self.apply_iup_scope(OreProductionsView.objects.all(), request)
        roa_qs  = self.apply_iup_scope(DetailsRoa.objects.all(), request)
        mral_qs = self.apply_iup_scope(DetailsMral.objects.all(), request)

        prod_qs = apply_common_filters(prod_qs, request.query_params)
        roa_qs  = apply_common_filters(roa_qs, request.query_params)
        mral_qs = apply_common_filters(mral_qs, request.query_params)

        return Response({
            "production_tonnage": sum_tonnage(prod_qs),
            "roa_tonnage": sum_tonnage(roa_qs),
            "mral_tonnage": sum_tonnage(mral_qs),
        })