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

def summary_hm_unit_kpi(request):
    iup_filter      = request.GET.get("iup_id")
    filter_type     = request.GET.get("filter_type")
    filter_year     = int(request.GET.get("year", 0) or 0)
    filter_month    = int(request.GET.get("month", 0) or 0)
    filter_week     = request.GET.get("week")
    filter_date     = request.GET.get("filter_date")
    date_start      = request.GET.get("date_start")
    date_end        = request.GET.get("date_end")
    vendor          = request.GET.get("vendor")
    categories_raw  = request.GET.get("categories", "[]")

    try:
        categories = json.loads(categories_raw)
    except Exception:
        categories = []

    # resolve date range
    try:
        if filter_type == "daily" and filter_date:
            ds = filter_date
            de = filter_date

        elif filter_type == "range" and date_start and date_end:
            ds = date_start
            de = date_end

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
                y = int(y_str)
                w = int(w_str)
                start = datetime.strptime(f"{y}-W{w:02d}-1", "%G-W%V-%u")
                end = start + timedelta(days=6)
                ds = start.strftime("%Y-%m-%d")
                de = end.strftime("%Y-%m-%d")
            else:
                y = filter_year
                m = filter_month
                w = int(filter_week)

                first_day = datetime(y, m, 1)
                start = first_day + timedelta(days=(w - 1) * 7)
                end = start + timedelta(days=6)

                if end.month != m:
                    last_day = calendar.monthrange(y, m)[1]
                    end = datetime(y, m, last_day)

                ds = start.strftime("%Y-%m-%d")
                de = end.strftime("%Y-%m-%d")

        elif filter_type == "all":
            ds = "2000-01-01"
            de = "2100-12-31"

        else:
            return JsonResponse({"error": "Invalid filter"}, status=400)

        datetime.strptime(ds, "%Y-%m-%d")
        datetime.strptime(de, "%Y-%m-%d")

    except Exception as e:
        return JsonResponse({"error": f"Invalid date filter: {str(e)}"}, status=400)

    try:
        query = """
            SELECT
                u.unit_vendor,
                TRIM(c.category) as category,
                COALESCE(SUM(f.volume), 0) AS fuel,
                COALESCE(SUM(CASE WHEN s.code = 'EWH' THEN d.duration_min END), 0) AS op,
                COALESCE(SUM(CASE WHEN s.code IN ('STB','SUPPORT','WX','SLP') THEN d.duration_min END), 0) AS st,
                COALESCE(SUM(CASE WHEN s.code IN ('PM','BD') THEN d.duration_min END), 0) AS mt,
                COALESCE(SUM(CASE WHEN s.code = 'BD' THEN d.duration_min END), 0) AS bd,
                COUNT(DISTINCT h.date) * 1440 AS total_time,
                ROUND(
                    COALESCE(
                        SUM(CASE WHEN s.code = 'EWH' THEN d.duration_min END)::numeric
                        / NULLIF(SUM(CASE WHEN s.code IN ('EWH','PM','BD') THEN d.duration_min END), 0),
                    0) * 100, 2
                ) AS ma,
                ROUND(
                    COALESCE(
                        SUM(CASE WHEN s.code IN ('EWH','STB','SUPPORT','WX','SLP') THEN d.duration_min END)::numeric
                        / NULLIF((COUNT(DISTINCT h.date) * 1440), 0),
                    0) * 100,
                    2
                ) AS pa,
                ROUND(
                    COALESCE(
                        SUM(CASE WHEN s.code = 'EWH' THEN d.duration_min END)::numeric
                        / NULLIF(SUM(CASE WHEN s.code IN ('EWH','STB','SUPPORT','WX','SLP') THEN d.duration_min END), 0),
                    0) * 100,
                    2
                ) AS ua,
                ROUND(
                    COALESCE(
                        SUM(CASE WHEN s.code = 'EWH' THEN d.duration_min END)::numeric
                        / NULLIF((COUNT(DISTINCT h.date) * 1440), 0),
                    0) * 100,
                    2
                ) AS eu
            FROM mining_hm_unit h
            LEFT JOIN master_units u ON u.id = h.unit_id
            LEFT JOIN mining_hm_unit_detail d ON d.hm_unit_id = h.id
            LEFT JOIN master_units_categories c ON c.id = u.id_category
            LEFT JOIN master_vendors v ON v.id = u.id_vendor
            LEFT JOIN master_activity_categories s ON s.id = d.status_id
            LEFT JOIN mining_fuel_consumption f ON f.unit = u.unit_code AND f.date = h.date
            WHERE h.date BETWEEN %s AND %s
        """

        params = [ds, de]

        iup_clause, iup_params = build_iup_clause(iup_filter, "h")
        query += iup_clause
        params.extend(iup_params)

        if categories:
            placeholders = ",".join(["%s"] * len(categories))
            query += f" AND LOWER(TRIM(c.category)) IN ({placeholders})"
            params.extend([c.lower().strip() for c in categories])

        if vendor:
            query += " AND v.id = %s"
            params.append(vendor)

        query += " GROUP BY u.unit_vendor, c.category ORDER BY u.unit_vendor"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        result = []
        for r in rows:
            result.append({
                "unit": r[0],
                "category": r[1],
                "fuel": round(float(r[2] or 0), 2),
                "op": min_to_hour(r[3]),
                "st": min_to_hour(r[4]),
                "mt": min_to_hour(r[5]),
                "bd": min_to_hour(r[6]),
                "time": min_to_hour(r[7]),
                "ma": float(r[8] or 0),
                "pa": float(r[9] or 0),
                "ua": float(r[10] or 0),
                "eu": float(r[11] or 0),
            })

        return JsonResponse({
            "success": True,
            "filter_type": filter_type,
            "date_start": ds,
            "date_end": de,
            "data": result
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)