# analytics/services/bot/services/fuel_service.py

from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict

from analytics.views.fuel.ratio import (
    get_fuel_ratio,
    get_fuel_ratio_ore,
)

from analytics.views.fuel.summary import (
    get_chart_fuel,
    get_chart_fuel_category,
)


def call_view(view_func, params):
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

    request = factory.get("/fuel/", data=query)

    response = view_func(request)

    return json_response_to_dict(response)


def simplify_fuel_chart(chart_data):

    y_data = chart_data.get("y_data", [])

    if not y_data:
        return {
            "grand_total": 0,
            "average": 0,
            "max": 0,
            "min": 0,
        }

    return {
        "grand_total": chart_data.get("grand_total", 0),
        "average": round(sum(y_data) / len(y_data), 2),
        "max": max(y_data),
        "min": min(y_data),
    }


def get_fuel_review_service(params):

    fuel_ratio = call_view(
        get_fuel_ratio,
        params
    )

    fuel_ratio_ore = call_view(
        get_fuel_ratio_ore,
        params
    )

    fuel_chart = call_view(
        get_chart_fuel,
        params
    )

    fuel_category = call_view(
        get_chart_fuel_category,
        params
    )

    return {
        "fuel_ratio": fuel_ratio.get("summary", {}),
        "fuel_ratio_ore": fuel_ratio_ore.get("summary", {}),
        "fuel_trend": simplify_fuel_chart(fuel_chart),
        "fuel_category": fuel_category.get("summary", []),
    }