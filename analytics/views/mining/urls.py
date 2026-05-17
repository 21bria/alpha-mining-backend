from django.urls import path

from .reserve import get_reserve_summary
from .all_summary import *
from .summary_by_material import *
from .details_ore import *
from .details_ob import *
from .details_others import *
from .details_quarry import *
from .details_topsoil import *
from .details_waste import *
from .fleet_kpi import *
from ..unit_activty.unit_activity_summary import *
from ..unit_activty.productivity import *
from ..unit_activty.kpi_monitoring import *

urlpatterns = [
    path('reserve/', get_reserve_summary),
    path('summary/', get_summary_mines),
    path('summary/materials/', get_summary_materials_grouped),
    path('chart/', get_chart_mining),
    path('chart/daily/', get_chart_ore_quality),
    path('chart-ore/', get_detail_ore),
    path('chart-ob/', get_detail_ob),
    path('chart-others/', get_detail_others),
    path('chart-quarry/', get_detail_quarry),
    path('chart-top-soil/', get_detail_top_soil),
    path('chart-waste/', get_detail_waste),
   

    # unit activity
    path('kpi/hauler/', get_kpi_hauler),
    path('kpi/digger/', get_kpi_digger),
    path('kpi-unit/summary/', summary_hm_unit_kpi),
    path('kpi-monitoring/', kpi_monitoring),

    # Productivity
    path('summary-productivity/ore/', summary_productivity_ore),
   
]