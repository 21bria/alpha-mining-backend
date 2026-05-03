from django.urls import path

from analytics.views.daily.fuel import get_daily_fuel_ratio, get_daily_fuel_ratio_ore, get_fuel_daily_report
from analytics.views.daily.reserve import get_reserve_summary_daily
from analytics.views.daily.weater import get_weather_grouped

from .mining import get_chart_daily_mining, get_summary_daily_mining,get_summary_materials,get_summary_materials_grouped
from .fleet_kpi import get_kpi_daily_digger, get_kpi_daily_hauler
from .details import *
# from .details_ore import *
# from .details_ob import *
# from .details_others import *
# from .details_quarry import *
# from .details_topsoil import *
# from .details_waste import *

urlpatterns = [
    path('reserve/', get_reserve_summary_daily),
    path('summary/mining/', get_summary_daily_mining),
    path('chart/', get_chart_daily_mining),
     path('chart/details/', get_daily_detail_productions, name='get_daily_detail_productions'),
    path('summary/materials/', get_summary_materials),
    path('summary/materials/grouped/', get_summary_materials_grouped),
    path('chart/details/', get_daily_detail_productions),
    # Weather
    path('summary/weather/grouped/', get_weather_grouped),
    # Kpi Hauler
    path('chart/kpi/hauler/', get_kpi_daily_hauler),
    # Kpi Digger
    path('chart/kpi/digger/', get_kpi_daily_digger),
    # Fuel
    path('summary/fuel/', get_fuel_daily_report),
    path('summary/fuel/ratio/', get_daily_fuel_ratio),
    path('summary/fuel/ratio/ore/', get_daily_fuel_ratio_ore),
    ]