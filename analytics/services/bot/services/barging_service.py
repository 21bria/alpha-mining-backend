from django.test import RequestFactory
from analytics.services.bot.utils.response import json_response_to_dict

from analytics.views.barging.data_group import (
    summary_barging_overview
)

from analytics.views.barging.selling import (
    summary_selling_overview
)

from analytics.services.bot.services.coa_service import (
    get_coa_compare
)


def _call_view(view_func, url, params):

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
    }

    query = {
        k: v for k, v in query.items()
        if v not in [None, ""]
    }

    request = factory.get(url, data=query)

    response = view_func(request)

    return json_response_to_dict(response)


def get_barging_overview(params):

    return _call_view(
        summary_barging_overview,
        "/barging-overview/",
        params
    )


def get_selling_overview(params):

    return _call_view(
        summary_selling_overview,
        "/selling-overview/",
        params
    )


def get_barging_review_service(params):

    barging = get_barging_overview(params)

    selling = get_selling_overview(params)

    coa = get_coa_compare(params)

    return {
        "barging_summary": barging,
        "selling_summary": selling,
        "coa_compare": coa,
    }