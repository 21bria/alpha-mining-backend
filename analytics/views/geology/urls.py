from django.urls import path
from .all_summary import *
from .details import *
from .sample_crm.get_data_roa import *
from .sample_crm.get_data_mral import *
from .sample_duplicated.get_roa import *
from .sample_duplicated.get_mral import *
from .sample_duplicated.get_wet_roa import *
from .sample_duplicated.get_wet_roa_raw import *
from .sample_duplicated.get_wet_mral import *
from .sample_duplicated.get_wet_mral_raw import *
from .lab_tat.get_type_count import *
from .lab_tat.get_type_section import *
from .lab_tat.get_laboratory_tat import *
from .grade_roa import *




urlpatterns = [
    path('summary/', get_ore_summary),
    path('ore-chart/', get_chart_ore),
    path('ore-class/', get_ore_class),
    # Details
    path('ore-chart/detail/', get_chart_detail_geology),
    path('ore-class/lim/', get_ore_class_lim),
    path('ore-class/sap/', get_ore_class_sap),
    path('sample-crm-roa/plot-data', get_data_crm_roa_plot_json),
    path('sample-crm-mral/plot-data', get_data_crm_mral_plot_json),
    path('sample-duplicated-roa/scatter', scatter_sample_duplicate),
    path('sample-duplicated-mral/scatter', scatter_sample_duplicate_mral),
    path('sample-duplicated-roa/wet', chart_wet_roa),
    path('sample-duplicated-roa/wet/raw', get_raw_wet_roa),
    path('sample-duplicated-mral/wet', chart_wet_mral),
    path('sample-duplicated-mral/wet/raw', get_raw_wet_mral),
   
    # Lab.
    path('lab-count-type', chart_type_count),
    path('lab-count-type/section', chart_sample_release_year),
    path('lab-count-section/range', chart_sample_type_range),
    # TAT
    path('chart-tat/roa', chart_tat_roa),
    path('data-tat/roa', get_data_roa_by_range),
    path('chart-tat/mral', chart_tat_mral),
    path('data-tat/mral', get_data_mral_by_range),
   
    # Grade Productions
     path('production-grade/', get_production_grade),


]