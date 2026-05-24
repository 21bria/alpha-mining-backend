from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict

from analytics.views.barging.coa import (
    niChartCoa,
    feChartCoa,
    mgoChartCoa,
    sio2ChartCoa,
    smChartCoa,
)


def _call_view(view_func, params):
    factory = RequestFactory()

    query = {
        "filter_type"   : params.get("filter_type"),
        "year"          : params.get("year"),
        "month"         : params.get("month"),
        "week"          : params.get("week"),
        "filter_date"   : params.get("filter_date"),
        "date_start"    : params.get("date_start"),
        "date_end"      : params.get("date_end"),
        "iup_id"        : params.get("iup_id"),
        "materialFilter": params.get("materialFilter"),
    }

    query = {
        k: v for k, v in query.items()
        if v not in [None, ""]
    }

    request = factory.get("/coa/", data=query)
    response = view_func(request)

    return json_response_to_dict(response)


def get_coa_compare(params):
    return {
        "ni"    : _call_view(niChartCoa, params),
        "fe"    : _call_view(feChartCoa, params),
        "mgo"   : _call_view(mgoChartCoa, params),
        "sio2"  : _call_view(sio2ChartCoa, params),
        "sm"    : _call_view(smChartCoa, params),
    }