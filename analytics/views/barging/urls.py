from django.urls import path
from .data_group import *
from .selling import *
from .coa import *
from .split_sample.range_monitoring import *
from ..barging.split_sample.range_summary import *
from ..barging.split_sample.range_re_assay import *
from .split_sample.range_shipment import *
from .split_sample.yearly_shipment import *

# management Report
from ..management.get_barging import *


urlpatterns = [
    path('summary/', get_barging_summary),
    path('chart/', get_chart_barging),
    path('summary-overview/', summary_barging_overview),

    path('summary-selling/', get_selling_summary),
    path('chart-selling/', get_chart_selling),
    path('summary-overview-selling/', summary_selling_overview),
    path('coa/ni/', niChartCoa),
    path('coa/fe/', feChartCoa),
    path('coa/mgo/', mgoChartCoa),
    path('coa/sio2/', sio2ChartCoa),
    path('coa/sm/', smChartCoa),
    path('coa/all/', allChartCoa),

    # Sample monitoring
    path('monitoring/sample/list/', samplesMonitoring),
    path('monitoring/sample/summary/', samplesMonitoringSummary),
    path('monitoring/sample/summary/re-assay/', samplesReAssaySummary),
    path('monitoring/shipment/summary/', shipmentSummaryBuyer),
    path('monitoring/shipment/summary/by-month/', shipmentSummaryByMonth),

    # management
    path('summary/management/', get_barging_management),

]