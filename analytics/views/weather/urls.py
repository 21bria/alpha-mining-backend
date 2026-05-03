from django.urls import path

from .data import *

urlpatterns = [   
    path('data/rainfall/', get_data_rainfall),
    path('data/weather/', get_data_weather),
    path('chart-rainfall/', get_chart_rainfall)
]