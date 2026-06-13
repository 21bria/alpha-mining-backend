from django.urls import path

from .reserve import get_reserve_summary
from .all_summary import *
from .summary_by_material import *
from .details_productions import *
from .details_ore import *
from .fleet_kpi import *
from ..unit_activty.unit_activity_summary import *
from ..unit_activty.productivity import *
from ..unit_activty.kpi_monitoring import *

# Management Report
from ..management.get_production import *
from ..management.get_inventory import *

urlpatterns = [
    path('reserve/', get_reserve_summary),
    path('summary/', get_summary_mines),
    path('summary/materials/', get_summary_materials_grouped),
    path('chart/', get_chart_mining),
    path('chart/daily/', get_chart_ore_quality),
    path('chart/details/', get_detail_material),
    path('chart-ore/', get_detail_ore),

    # unit activity
    path('kpi/hauler/', get_kpi_hauler),
    path('kpi/digger/', get_kpi_digger),
    path('kpi-unit/summary/', summary_hm_unit_kpi),
    path('kpi-monitoring/', kpi_monitoring),

    # Productivity
    path('summary-productivity/ore/', summary_productivity_ore),

    # Management
    path('summary/management/', get_summary_management),
    path('inventory/management/', get_inventory_management),
   
]