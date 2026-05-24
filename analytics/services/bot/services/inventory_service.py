from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict

from analytics.views.inventory.all_data import (
    get_inventory_summary,
    get_chart_inventory,
)

from analytics.views.inventory.cut_grade import (
    get_inventory_grade_cutoff,
)


def call_inventory_view(view_func, params):

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

    query = {
        k: v for k, v in query.items()
        if v not in [None, ""]
    }

    request = factory.get("/inventory/", data=query)

    response = view_func(request)

    return json_response_to_dict(response)


def get_inventory_summary_data(params):
    return call_inventory_view(get_inventory_summary, params)


def get_inventory_chart_data(params):
    return call_inventory_view(get_chart_inventory, params)


def get_inventory_review_service(params):
    summary = get_inventory_summary_data(params)
    chart = get_inventory_chart_data(params)
    cut_grade = get_inventory_grade_cutoff(params)

    return {
        "inventory_summary": summary,
        "inventory_chart": chart,
        "inventory_cut_grade": cut_grade,
    }