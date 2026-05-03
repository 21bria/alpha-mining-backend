from .headers.selling_official import SELLING_OFFICIAL_HEADERS
from .headers.selling_code import SELLING_CODE_HEADERS
from .headers.assay_roa import ASSAY_ROA_HEADERS
from .headers.assay_mral import ASSAY_MRAL_HEADERS
from .headers.waybills import WAYBILLS_HEADERS
from .headers.geology_samples import SAMPLES_GEOLOGY_HEADERS
from .headers.selling_samples import SAMPLES_SELLING_HEADERS
from .headers.selling_barging import SELLING_BARGING_HEADERS
from .headers.geology_ore import ORE_GEOLOGY_HEADERS
from .headers.mining_fuel import FUEL_TRANSPOSE_HEADERS
from .headers.master_units import MASTER_UNIT_HEADERS
from .headers.plan_barging import PLAN_BARGING_TRANSPOSE_HEADERS

HEADER_REGISTRY = {
    "selling.official"    : SELLING_OFFICIAL_HEADERS,
    "master.selling_code" : SELLING_CODE_HEADERS,
    "lab.assay_roa"       : ASSAY_ROA_HEADERS,
    "lab.assay_marl"      : ASSAY_MRAL_HEADERS,
    "geology.waybills"    : WAYBILLS_HEADERS,
    "geology.samples"     : SAMPLES_GEOLOGY_HEADERS,
    "selling.barging"     : SELLING_BARGING_HEADERS,
    "selling.samples"     : SAMPLES_SELLING_HEADERS,
    "geology.ore"         : ORE_GEOLOGY_HEADERS,
    # "mining.fuel"         : FUEL_TRANSPOSE_HEADERS,
    "master.mine_units"   : MASTER_UNIT_HEADERS,
}