
import logging
from django.http import JsonResponse
from django.db import connection
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause

def get_weather_grouped(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    data = summary_weather_grouped(filter_date, iup_filter)
    return JsonResponse(data, safe=False)


def summary_weather_grouped(filter_date, iup_filter=None):
    mw_iup_clause, mw_iup_params = build_iup_clause(iup_filter, "mw")

    query = f"""
        SELECT 
            mw.shift,
            mw.category,
            SUM(COALESCE(mw.duration, 0)) AS duration_min
        FROM mining_weather mw
        WHERE mw.date = %s::date
        {mw_iup_clause}
        GROUP BY mw.shift, mw.category
        ORDER BY mw.shift, mw.category;
    """

    params = [filter_date] + mw_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    result = []
    for shift, category, duration_min in rows:
        duration_min = float(duration_min or 0)
        duration_hour = round(duration_min / 60, 2)

        result.append({
            "shift": shift,
            "category": category,
            "duration_min": duration_min,
            "duration_hour": duration_hour
        })

    return result