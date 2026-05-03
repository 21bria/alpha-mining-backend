from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import calendar
from datetime import datetime, timedelta
from django.db import connection
import json 
from datetime import datetime
from analytics.services.iup_filter import build_iup_clause

def min_to_hour(m):
    return round((m or 0) / 60, 2)
from django.http import JsonResponse
from django.db import connection
import calendar
from datetime import datetime, timedelta


def summary_productivity_ore(request):
    iup_filter      = request.GET.get("iup_id")
    filter_type     = request.GET.get("filter_type")
    filter_year     = int(request.GET.get("year", 0) or 0)
    filter_month    = int(request.GET.get("month", 0) or 0)
    filter_week     = request.GET.get("week")
    filter_date     = request.GET.get("filter_date")
    date_start      = request.GET.get("date_start")
    date_end        = request.GET.get("date_end")

    # RESOLVE DATE RANGE
    try:
        if filter_type == "daily" and filter_date:
            ds = de = filter_date

        elif filter_type == "range" and date_start and date_end:
            ds, de = date_start, date_end

        elif filter_type == "monthly" and filter_year and filter_month:
            last_day = calendar.monthrange(filter_year, filter_month)[1]
            ds = f"{filter_year}-{filter_month:02d}-01"
            de = f"{filter_year}-{filter_month:02d}-{last_day:02d}"

        elif filter_type == "yearly" and filter_year:
            ds = f"{filter_year}-01-01"
            de = f"{filter_year}-12-31"

        elif filter_type == "weekly" and filter_week:
            if "-" in str(filter_week):
                y_str, w_str = str(filter_week).split("-")
                start = datetime.strptime(f"{y_str}-W{int(w_str):02d}-1", "%G-W%V-%u")
                end = start + timedelta(days=6)
            else:
                y, m, w = filter_year, filter_month, int(filter_week)
                first_day = datetime(y, m, 1)
                start = first_day + timedelta(days=(w - 1) * 7)
                end = start + timedelta(days=6)
                if end.month != m:
                    end = datetime(y, m, calendar.monthrange(y, m)[1])

            ds, de = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

        elif filter_type == "all":
            ds, de = "2000-01-01", "2100-12-31"

        else:
            return JsonResponse({"error": "Invalid filter"}, status=400)

        datetime.strptime(ds, "%Y-%m-%d")
        datetime.strptime(de, "%Y-%m-%d")

    except Exception as e:
        return JsonResponse({"error": f"Invalid date filter: {str(e)}"}, status=400)

    # WHERE CLAUSE
    where_clause = "date_production BETWEEN %s AND %s"
    params = [ds, de]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_clause += f" AND iup_id IN ({placeholders})"
            params += iup_ids

    # SUMMARY QUERY
    summary_sql = f"""
        SELECT
            COALESCE(SUM(total_tonnage), 0),
            COALESCE(SUM(working_hours), 0),
            COALESCE(COUNT(DISTINCT loader), 0),
            COALESCE(
                ROUND(
                    (SUM(total_tonnage) / NULLIF(SUM(working_hours), 0))::numeric,
                    2
                ),
                0
            )
        FROM view_mining_loader_ore_productivity
        WHERE {where_clause}
    """

    # DYNAMIC GROUPING
    if filter_type == "yearly":
        group_select = "TO_CHAR(date_production, 'YYYY-MM')"
        group_label  = "TO_CHAR(date_production, 'Mon YY')"
        group_order  = "TO_CHAR(date_production, 'YYYY-MM')"

    elif filter_type == "all":
        group_select = "TO_CHAR(date_production, 'YYYY')"
        group_label  = "TO_CHAR(date_production, 'YYYY')"
        group_order  = "TO_CHAR(date_production, 'YYYY')"

    else:
        group_select = "date_production"
        group_label  = "date_production::text"
        group_order  = "date_production"

    # CHART QUERY
    chart_sql = f"""
        SELECT
            {group_label} AS label,
            COALESCE(SUM(total_tonnage), 0),
            COALESCE(SUM(working_hours), 0),
            COALESCE(COUNT(DISTINCT loader), 0),
            COALESCE(
                ROUND(
                    (SUM(total_tonnage) / NULLIF(SUM(working_hours), 0))::numeric,
                    2
                ),
                0
            )
        FROM view_mining_loader_ore_productivity
        WHERE {where_clause}
        GROUP BY {group_select}, {group_label}
        ORDER BY {group_order}
    """

    # EXECUTE QUERY
    with connection.cursor() as cursor:
        cursor.execute(summary_sql, params)
        s = cursor.fetchone()

        cursor.execute(chart_sql, params)
        rows = cursor.fetchall()

    # RESPONSE
    return JsonResponse({
        "summary": {
            "total_ore": float(s[0] or 0),
            "total_hours": float(s[1] or 0),
            "fleet": int(s[2] or 0),
            "productivity": float(s[3] or 0),
        },
        "x_data": [r[0] for r in rows],
        "total_ore": [float(r[1] or 0) for r in rows],
        "working_hours": [float(r[2] or 0) for r in rows],
        "fleet": [int(r[3] or 0) for r in rows],
        "productivity": [float(r[4] or 0) for r in rows],
        "meta": {
            "date_start": ds,
            "date_end": de,
            "filter_type": filter_type,
        }
    })