from django.urls import path
from .all_data import *
# from .details import *


urlpatterns = [
    path('summary/', get_inventory_summary),
    path('chart/', get_chart_inventory),
    path('grade-roa/', get_grade_roa),
]