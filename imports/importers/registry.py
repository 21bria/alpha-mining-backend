# imports/importers/registry.py
from .tables.master_selling_code import SellingCodeImporter
from .tables.activities_locations import ActivitiesLocationsImporter


from .tables.geology_assay_roa import AssayRoaImporter
from .tables.geology_assay_mral import AssayMralImporter
from .tables.geology_waybills import WaybillsImporter
from .tables.geology_samples import SamplesImporter
from .tables.geology_ore_productions import OreProductionImporter

from .tables.mining_planing import MiningPlanningImporter
from .tables.mining_productions import MiningProductionImporter
from .tables.mining_fuel_daily import MiningFuelTransposeImporter
from .tables.mine_units import MineUnitImporter
from .tables.mining_rainfall import MiningRainfallImporter
from .tables.mining_weather import MiningWeatherImporter
from .tables.mining_activity import MiningActivityImporter
from .tables.mining_activity_units import MiningActivityUnitsImporter
from .tables.mining_fill_factor import MiningFillFactorImporter


from .tables.selling_samples import SamplesSellingImporter
from .tables.selling_barge import SellingBargeImporter
from .tables.selling_barge import SellingBargeImporter
from .tables.selling_official_importer import SellingOfficialImporter
from .tables.selling_plan_barging import BargingPlanTransposeImporter

IMPORTER_REGISTRY = {
    # Master
    "master.selling_code"         : SellingCodeImporter,
    "master.mine_units"           : MineUnitImporter,
    "master.activities_locations" : ActivitiesLocationsImporter,

    # Geology
    "lab.assay_roa"           : AssayRoaImporter,
    "lab.assay_mral"          : AssayMralImporter,
    "geology.waybills"        : WaybillsImporter,
    "geology.samples"         : SamplesImporter,
    "selling.samples"         : SamplesSellingImporter,
    "geology.ore"             : OreProductionImporter,

    # Mining
    "mining.plan_productions" : MiningPlanningImporter,
    "mining.productions"      : MiningProductionImporter,
    "mining.fuel_daily"       : MiningFuelTransposeImporter,
    "mining.rainfall"         : MiningRainfallImporter,
    "mining.weather"          : MiningWeatherImporter,
    "mining.activity"         : MiningActivityImporter,
    "mining.activity_units"   : MiningActivityUnitsImporter,
    "mining.fill_factor"      : MiningFillFactorImporter,


    #Selling
    "selling.barging"         : SellingBargeImporter,
    "selling.official"        : SellingOfficialImporter,
    "selling.barging_plan"    : BargingPlanTransposeImporter,
    
}
