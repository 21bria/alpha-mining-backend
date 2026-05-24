from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict
from analytics.services.bot.utils.clean_params import  clean_service_params

from analytics.views.weather.data import (
    get_data_weather,
    get_data_rainfall,
    get_chart_rainfall,
)

from analytics.services.bot.services.production_service import (
    get_summary_service
)

def call_weather_view(view_func, params):
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

    request = factory.get("/weather/", data=query)
    response = view_func(request)

    return json_response_to_dict(response)


def simplify_rainfall_chart(chart):
    y_data = chart.get("y_data", [])

    if not y_data:
        return {
            "grand_total": 0,
            "average": 0,
            "max": 0,
            "min": 0,
        }

    return {
        "grand_total": chart.get("grand_total", 0),
        "average": round(sum(y_data) / len(y_data), 2),
        "max": max(y_data),
        "min": min(y_data),
    }

def get_weather_review_service(params):
    weather = call_weather_view(get_data_weather, params)
    rainfall = call_weather_view(get_data_rainfall, params)
    rainfall_chart = call_weather_view(get_chart_rainfall, params)

    production_params = clean_service_params(params)

    production = get_summary_service(**production_params)

    rainy_minutes = float(weather.get("rainy", 0))
    slippery_minutes = float(weather.get("slippery", 0))

    weather_duration = {
        "rainy_hours": round(rainy_minutes / 60, 1),
        "slippery_hours": round(slippery_minutes / 60, 1),
    }

    return {
        "weather_duration": weather_duration,
        "rainfall_average": rainfall,
        "rainfall_trend": simplify_rainfall_chart(rainfall_chart),
        "production_summary": production,
        "chat_context": params.get("chat_context", []),
    }