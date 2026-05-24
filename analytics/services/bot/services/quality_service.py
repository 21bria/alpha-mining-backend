from analytics.services.bot.utils.response import json_response_to_dict
from django.test import RequestFactory
from analytics.views.geology.grade_roa import get_production_grade


def get_quality_review_service(params):
    factory = RequestFactory()

    query = {
        "filter_type": params.get("filter_type", "monthly"),
        "year": params.get("year"),
        "month": params.get("month"),
        "week": params.get("week"),
        "filter_date": params.get("filter_date"),
        "date_start": params.get("date_start"),
        "date_end": params.get("date_end"),
        "iup_id": params.get("iup_id"),
        "material": params.get("material"),
    }

    query = {k: v for k, v in query.items() if v not in [None, ""]}

    request = factory.get("/production-grade/", data=query)
    response = get_production_grade(request)

    return json_response_to_dict(response)