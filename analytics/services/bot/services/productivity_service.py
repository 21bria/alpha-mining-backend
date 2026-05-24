# analytics/services/bot/services/productivity_service.py

from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict


from analytics.views.unit_activty.productivity import (
    summary_productivity_ore,
)


def call_productivity_view(view_func, params):
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

    request = factory.get("/productivity/", data=query)
    response = view_func(request)

    return json_response_to_dict(response)


def simplify_productivity_chart(data):
    productivity = data.get("productivity", [])

    if not productivity:
        return {
            "average": 0,
            "max": 0,
            "min": 0,
        }

    return {
        "average": round(sum(productivity) / len(productivity), 2),
        "max": max(productivity),
        "min": min(productivity),
    }


def get_productivity_service(params):
    ore_productivity = call_productivity_view(
        summary_productivity_ore,
        params
    )

    return {
        "ore_productivity_summary": ore_productivity.get("summary", {}),
        "ore_productivity_trend": simplify_productivity_chart(ore_productivity),
        "meta": ore_productivity.get("meta", {}),
    }