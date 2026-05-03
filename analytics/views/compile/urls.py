from django.urls import path

from analytics.services.compile.generate_excel import *
from analytics.services.compile.generate_pdf import *
from analytics.services.export.xls.generate import export_module_excel
from analytics.services.export.xls.generate_coa import export_excel_coa

urlpatterns = [
    # Task list
    path('generate/excel/', excel_unified_summary, name='excel_unified_summary'),
    path('generate/pdf/', pdf_unified_summary, name='pdf_unified_summary'),
    path('export/data/xlsx/', export_module_excel, name='export_module_excel'),
    path('export/coa/xlsx/', export_excel_coa, name='excel_unified_coa'),
]     