from django.urls import path
from .summary import *
from .ratio import *


urlpatterns = [
    path('chart/', get_chart_fuel),
    path('chart/category/', get_chart_fuel_category),
    path('ratio/', get_fuel_ratio),
    path('ratio-ore/', get_fuel_ratio_ore),
]