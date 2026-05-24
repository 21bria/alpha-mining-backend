from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict

from analytics.views.mining.fleet_kpi import (
    get_kpi_hauler,
    get_kpi_digger,
)


def _call_view(view_func, params):
    factory = RequestFactory()

    query = {
        "filter_type": params.get("filter_type"),
        "year": params.get("year"),
        "month": params.get("month"),
        "week": params.get("week"),
        "filter_date": params.get("filter_date"),
        "date_start": params.get("date_start"),
        "date_end": params.get("date_end"),
        "iup_id": params.get("iup_id"),
    }

    query = {k: v for k, v in query.items() if v not in [None, ""]}

    request = factory.get("/fleet-kpi/", data=query)
    response = view_func(request)

    return json_response_to_dict(response)


def get_equipment_review_service(params):
    hauler = _call_view(get_kpi_hauler, params)
    digger = _call_view(get_kpi_digger, params)

    return {
        "hauler_kpi": hauler,
        "digger_kpi": digger,
    }