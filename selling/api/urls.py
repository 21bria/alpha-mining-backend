from django.urls import path, include
from rest_framework.routers import DefaultRouter

from selling.api.barging.views import SellingViewSet,SellingBargingCRUDViewSet
from selling.api.temporary.views import SellingTemporaryViewSet,SellingBargingTemporaryCRUDViewSet
from selling.api.barging.ore_sum_views import TonnageByCodeAPIView
from selling.api.official.views import SellingOfficialViewSet,SellingOfficialCRUDViewSet
from selling.api.samples.views import SamplesViewSet,SamplesViewCRUDSet
from selling.api.adjustment.views import SellingBargingAdjustmentViewSet
from selling.api.plan.views import BargingPlanViewSet

router = DefaultRouter()

router.register(r"barging", SellingViewSet, basename="selling-barging")
router.register(r"barging-crud", SellingBargingCRUDViewSet, basename="selling-barging-crud")
# temporary
router.register(r"temporary", SellingTemporaryViewSet, basename="selling-temporary")
router.register(r"temporary-crud", SellingBargingTemporaryCRUDViewSet, basename="temporary-barging-crud")

router.register(r"code-adjust", SellingBargingAdjustmentViewSet, basename="code-adjust")

router.register(r"official-view", SellingOfficialViewSet, basename="official-view")
router.register(r"official", SellingOfficialCRUDViewSet, basename="official-crud")
router.register(r"samples", SamplesViewSet, basename="samples")
router.register(r"samples-crud", SamplesViewCRUDSet, basename="samples-crud")
# Paln Barging
router.register(r"plan-barging", BargingPlanViewSet, basename="plan-barging")

urlpatterns = [
     path("barging/tonnage-by-code/", TonnageByCodeAPIView.as_view(), name="barging-tonnage-by-code"),
    *router.urls,
]