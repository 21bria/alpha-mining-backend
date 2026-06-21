from django.urls import path, include
from rest_framework.routers import DefaultRouter

from master.api.iup.views import MineIUPViewSet
from master.api.lookups.units_categories import UnitsCategoriesListView
from master.api.source.views import SourceMinesViewSet
from master.api.loading.views import SourceMinesLoadingViewSet
from master.api.dome_pit.views import SourcePitDomeViewSet
from master.api.dumping.views import SourceMinesDumpingViewSet
from master.api.dome.views import SourceMinesDomeViewSet
from master.api.block.views import BlockViewSet
from master.api.materials.views import MaterialViewSet
from master.api.vendor.views import VendorsViewSet
from master.api.units_mine.views import MineUnitsViewSet, UnitAssignmentViewSet, UnitsCategoriesViewSet
from master.api.sale_code.views import SellingCodeViewSet
from master.api.sale_surveyor.views import SellingSurveyorViewSet
from master.api.sale_factory.views import StockFactoriesViewSet
from master.api.barge.views import BargeUnitsViewSet
from master.api.activity.views import MiningActivityViewSet,MiningActivityCategoriesViewSet
from master.api.activity_locations.views import MiningActivityLocationViewSet
from master.api.ore_class.views import OreClassViewSet
from master.api.ore_fill_factors.views import OreTruckFactorViewSet

from master.api.sample.views import SampleTypeViewSet, SampleMethodViewSet
from master.api.grade_control.views import MineGeologiesViewSet

from master.api.settings.production.views import ProductionConfigViewSet
from master.api.settings.quality.views import QualityConfigViewSet



router = DefaultRouter()
router.register(r"materials", MaterialViewSet, basename="materials")
router.register(r"iup", MineIUPViewSet, basename="iup")
router.register(r"mine-sources", SourceMinesViewSet, basename="mine-sources")
router.register(r"mine-block", BlockViewSet, basename="mine-block")
router.register(r"loading-points", SourceMinesLoadingViewSet, basename="loading-points")
router.register(r"pit-dome", SourcePitDomeViewSet, basename="pit-dome")

router.register(r"dumping-points", SourceMinesDumpingViewSet, basename="dumping-points")
router.register(r"dome-points", SourceMinesDomeViewSet, basename="dome-points")
router.register(r"vendors", VendorsViewSet, basename="vendors")
router.register(r"units/categories", UnitsCategoriesViewSet, basename="units-categories")
router.register(r"mine-units", MineUnitsViewSet, basename="mine-units")
router.register(r"unit-assignments", UnitAssignmentViewSet, basename="unit-assignments")
router.register(r"selling-code", SellingCodeViewSet, basename="selling-code")
router.register(r"selling-surveyor", SellingSurveyorViewSet, basename="selling-surveyor")
router.register(r"stock-factories", StockFactoriesViewSet, basename="stock-factories")
router.register(r"barge", BargeUnitsViewSet, basename="barge")
router.register(r"activity", MiningActivityViewSet, basename="activity")
router.register(r"activity-categories", MiningActivityCategoriesViewSet, basename="activity-categories")
router.register(r"activity-locations", MiningActivityLocationViewSet, basename="activity-locations")
router.register(r"ore-class", OreClassViewSet, basename="ore-class")
router.register(r"fill-factors", OreTruckFactorViewSet, basename="fill-factors")
router.register(r'sample-types', SampleTypeViewSet, basename='sample-types')
router.register(r'sample-methods', SampleMethodViewSet,basename='sample-method')
router.register(r'grade-control', MineGeologiesViewSet,basename='grade-control')

router.register(r"production-config",ProductionConfigViewSet,basename="production-config")
router.register(r"quality-config",QualityConfigViewSet,basename="quality-config")

urlpatterns = [
    path("lookups/", include("master.api.lookups.urls")),  # call urls lookups ini penting
    path("lookups/categories-units/", UnitsCategoriesListView.as_view(), name="categories-units-list"),
    *router.urls,
]