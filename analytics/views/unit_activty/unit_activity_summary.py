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
        extra_where = ""
        params = [ds, de]

        iup_clause, iup_params = build_iup_clause(iup_filter, "h")
        extra_where += iup_clause
        params.extend(iup_params)

        if categories:
            placeholders = ",".join(["%s"] * len(categories))
            extra_where += f" AND LOWER(TRIM(c.category)) IN ({placeholders})"
            params.extend([x.lower().strip() for x in categories])

        if vendor:
            extra_where += " AND u.id_vendor = %s"
            params.append(vendor)

        query = f"""
            WITH filtered_hm AS (
                SELECT
                    h.id,
                    h.date,
                    u.unit_code,
                    u.unit_vendor,
                    TRIM(c.category) AS category
                FROM mining_hm_unit h
                LEFT JOIN master_units u ON u.id = h.unit_id
                LEFT JOIN master_units_categories c ON c.id = u.id_category
                WHERE h.date BETWEEN %s AND %s
                {extra_where}
            ),
            activity AS (
                SELECT
                    fh.unit_vendor,
                    fh.category,

                    COALESCE(SUM(CASE WHEN s.code = 'EWH' THEN d.duration_min ELSE 0 END), 0) AS ewh_min,
                    COALESCE(SUM(CASE WHEN s.code IN ('STB','SUPPORT','WX','SLP') THEN d.duration_min ELSE 0 END), 0) AS standby_min,
                    COALESCE(SUM(CASE WHEN s.code IN ('PM','BD') THEN d.duration_min ELSE 0 END), 0) AS maintenance_min,
                    COALESCE(SUM(CASE WHEN s.code = 'BD' THEN d.duration_min ELSE 0 END), 0) AS bd_min,

                    COUNT(DISTINCT fh.unit_code || '-' || fh.date) * 1440 AS total_time_min

                FROM filtered_hm fh
                LEFT JOIN mining_hm_unit_detail d ON d.hm_unit_id = fh.id
                LEFT JOIN master_activity_categories s ON s.id = d.status_id
                GROUP BY fh.unit_vendor, fh.category
            ),
            fuel_sum AS (
                SELECT
                    fh.unit_vendor,
                    fh.category,
                    COALESCE(SUM(f.volume), 0) AS fuel
                FROM filtered_hm fh
                LEFT JOIN mining_fuel_consumption f
                    ON f.unit = fh.unit_code
                    AND f.date = fh.date
                GROUP BY fh.unit_vendor, fh.category
            )
            SELECT
                a.unit_vendor,
                a.category,
                ROUND(COALESCE(f.fuel, 0)::numeric, 2) AS fuel,

                ROUND(a.ewh_min::numeric / 60, 2) AS working,
                ROUND(a.standby_min::numeric / 60, 2) AS standby,
                ROUND(a.maintenance_min::numeric / 60, 2) AS maintenance,
                ROUND(a.bd_min::numeric / 60, 2) AS bd,
                ROUND(a.total_time_min::numeric / 60, 2) AS time,

                ROUND(COALESCE(a.ewh_min::numeric / NULLIF(a.ewh_min + a.maintenance_min, 0), 0) * 100, 2) AS ma,
                ROUND(COALESCE((a.ewh_min + a.standby_min)::numeric / NULLIF(a.total_time_min, 0), 0) * 100, 2) AS pa,
                ROUND(COALESCE(a.ewh_min::numeric / NULLIF(a.ewh_min + a.standby_min, 0), 0) * 100, 2) AS ua,
                ROUND(COALESCE(a.ewh_min::numeric / NULLIF(a.total_time_min, 0), 0) * 100, 2) AS eu,

                ROUND(
                    (
                        a.total_time_min -
                        (a.ewh_min + a.standby_min + a.maintenance_min)
                    )::numeric / 60,
                    2
                ) AS missing_hour,

                CASE
                    WHEN (a.ewh_min + a.standby_min + a.maintenance_min) = a.total_time_min
                        THEN 'Complete'
                    WHEN (a.ewh_min + a.standby_min + a.maintenance_min) < a.total_time_min
                        THEN 'Incomplete'
                    ELSE 'Over'
                END AS status

            FROM activity a
            LEFT JOIN fuel_sum f
                ON f.unit_vendor = a.unit_vendor
                AND f.category = a.category
            ORDER BY a.unit_vendor, a.category
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        result = []
        for r in rows:
            result.append({
                "unit": r[0],
                "category": r[1],
                "fuel": round(float(r[2] or 0), 2),
                "op": float(r[3] or 0),
                "st": float(r[4] or 0),
                "mt": float(r[5] or 0),
                "bd": float(r[6] or 0),
                "time": float(r[7] or 0),
                "ma": float(r[8] or 0),
                "pa": float(r[9] or 0),
                "ua": float(r[10] or 0),
                "eu": float(r[11] or 0),
                "missing_hour": float(r[12] or 0),
                "status": r[13],
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