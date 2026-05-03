from django.urls import path, include
from rest_framework.routers import DefaultRouter

from geology.api.assay_mral.views import AssayMralViewSet
from geology.api.assay_roa.views import AssayRoaViewSet
from geology.api.productions.production_compare_summary import ProductionCompareSummaryView
from geology.api.waybills.views import WaybillsViewSet,WaybillsViewCRUDSet
from geology.api.samples.views import SamplesViewSet,SamplesViewCRUDSet
from geology.api.productions.views import ProductionsViewSet,ProductionsViewCRUDSet
from geology.api.productions.details.views import ProductionsDetailsViewSet
from geology.api.productions.ore_sum_views import TonnageByDomeAPIView

from geology.api.dome_setup.views import DomeStatusCloseViewSet,DomeStatusFinishViewSet
from geology.api.dome_adjust.views import DomeAdjustmentViewSet
from geology.api.merge_pds.dome.views import DomeMergeViewSet
from geology.api.sample_crm.views import CRMCertificateViewSet



router = DefaultRouter()
router.register(r"lab-assay-mral", AssayMralViewSet, basename="lab-assay-mral")
router.register(r"lab-assay-roa", AssayRoaViewSet, basename="lab-assay-roa")
router.register(r"waybills", WaybillsViewSet, basename="waybills")
router.register(r"waybills-crud", WaybillsViewCRUDSet, basename="waybills-crud")
router.register(r"samples", SamplesViewSet, basename="samples")
router.register(r"samples-crud", SamplesViewCRUDSet, basename="samples-crud")
router.register(r"productions", ProductionsViewSet, basename="productions")
router.register(r"productions-crud", ProductionsViewCRUDSet, basename="productions-crud")
router.register(r"productions-detail", ProductionsDetailsViewSet, basename="productions-detail")
router.register(r"close-dome", DomeStatusCloseViewSet, basename="close-dome")
router.register(r"finish-dome", DomeStatusFinishViewSet, basename="finish-dome")
router.register(r"dome-adjust", DomeAdjustmentViewSet, basename="dome-adjust")
router.register(r"dome-merge", DomeMergeViewSet, basename="dome-merge")
router.register(r"crm-certified", CRMCertificateViewSet, basename="crm-certified")


urlpatterns = [
    path("ore-productions/tonnage-by-pile/", TonnageByDomeAPIView.as_view()),
    path("production-compare-summary/", ProductionCompareSummaryView.as_view(), name="production-compare-summary",),
    *router.urls,
   
]