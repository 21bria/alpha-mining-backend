from rest_framework.routers import DefaultRouter
from .grade_control import GradeControlLookupViewSet
from .selling_code import SellingCodeLookupViewSet
from .selling_discharge import DischargeLookupViewSet
from .barge import BargeLookupViewSet
from .materials import MaterialLookupViewSet
from .mine_iup import MineIUPLookupViewSet
from .mine_categories import MineCategoryLookupViewSet
from .mine_source import SourceMinesLookupViewSet
from .mine_block import BlockLookupViewSet
from .mine_loading import SourceMinesLoadingLookupViewSet
from .mine_dumping import SourceMinesDumpingLookupViewSet
from .mine_dome import SourceMinesDomeLookupViewSet
from .ore_class import OreClassLookupViewSet
from .ore_truck_factor import OreTruckFactorLookupViewSet

from .vendors import VendorsLookupViewSet
from .units_categories import UnitsCategoriesLookupViewSet
from .sample_type import SampleTypeLookupViewSet
from .sample_method import SampleMethodLookupViewSet
from .rainfall_points import RanfallPointsLookupViewSet
from .activity_categories import ActivityCategoriesLookupViewSet
from .mining_activity import ActivityLookupViewSet
from .mining_activity_location import ActivityLocationLookupViewSet
from .mining_units import MineUnitsLookupViewSet
from .sample_crm import CRMCertificateLookupViewSet

router = DefaultRouter()
router.register(r"grade-control", GradeControlLookupViewSet, basename="grade-control-lookup")
router.register(r"material", MaterialLookupViewSet, basename="material-lookup")
router.register(r"selling-code", SellingCodeLookupViewSet, basename="selling-code-lookup")
router.register(r"selling-discharge", DischargeLookupViewSet, basename="selling-discharge-lookup")
router.register(r"barge", BargeLookupViewSet, basename="selling-barge-lookup")
router.register(r"mine-categories", MineCategoryLookupViewSet, basename="mine-categories-lookup")
router.register(r"mine-iup", MineIUPLookupViewSet, basename="mine-iup-lookup")
router.register(r"mine-source", SourceMinesLookupViewSet, basename="mine-source-lookup")
router.register(r"mine-block", BlockLookupViewSet, basename="mine-block-lookup")
router.register(r"mine-loading", SourceMinesLoadingLookupViewSet, basename="mine-loading-lookup")
router.register(r"mine-dumping", SourceMinesDumpingLookupViewSet, basename="mine-dumping-lookup")
router.register(r"mine-dome", SourceMinesDomeLookupViewSet, basename="mine-dome-lookup")
router.register(r"ore-class", OreClassLookupViewSet, basename="ore-class-lookup")
router.register(r"ore-truck-factors", OreTruckFactorLookupViewSet, basename="ore-truck-factors-lookup")


router.register(r"vendors", VendorsLookupViewSet, basename="vendors-lookup")
router.register(r"units-categories", UnitsCategoriesLookupViewSet, basename="units-categories-lookup")
router.register(r"sample-type", SampleTypeLookupViewSet, basename="sample-type-lookup")
router.register(r"sample-method", SampleMethodLookupViewSet, basename="sample-method-lookup")

router.register(r"rainfall-points", RanfallPointsLookupViewSet, basename="rainfall-points-lookup")
router.register(r"activity-categories", ActivityCategoriesLookupViewSet, basename="lookup-activity-categories")
router.register(r"activities", ActivityLookupViewSet, basename="lookup-activities")
router.register(r"activity-locations", ActivityLocationLookupViewSet, basename="lookup-activity-locations")
router.register(r"mine-units", MineUnitsLookupViewSet, basename="lookup-mine-units")

router.register(r"crm-certificates", CRMCertificateLookupViewSet, basename="lookup-crm-certificates")



urlpatterns = router.urls