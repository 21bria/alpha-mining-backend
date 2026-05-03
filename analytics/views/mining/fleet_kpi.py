# views.py
import logging
from django.http import JsonResponse
from django.db import connection
from datetime import date, timedelta
import calendar
from analytics.services.iup_filter import build_iup_clause

def parse_iso_week(week_str: str):
    try:
        year_str, week_str = week_str.split("-")
        year = int(year_str)
        week = int(week_str)

        if week < 1 or week > 53:
            raise ValueError("Week must be between 1 and 53")

        return year, week
    except Exception:
        raise ValueError(f"Invalid ISO week format: {week_str}")

def min_to_hhmm(minutes):
    minutes = int(minutes or 0)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

# Kpi Daily Mining
def min_to_hour(m):
    return round((m or 0) / 60, 2)

def get_kpi_hauler(request):
    return summary_kpi_unit(
        request=request,
        production_unit_field="hauler",
        unit_type="hauler",
    )

def get_kpi_digger(request):
    return summary_kpi_unit(
        request=request,
        production_unit_field="loader",
        unit_type="digger",
    )

def summary_kpi_unit(request, production_unit_field, unit_type):
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    week        = request.GET.get("week")
    date_val    = request.GET.get("filter_date") or request.GET.get("date")
    date_start  = request.GET.get("date_start")
    date_end    = request.GET.get("date_end")
    iup_filter  = request.GET.get("iup_id")

    try:
        mp_where, mp_params = build_unit_date_filter_clause(
            filter_type=filter_type,
            year=year,
            month=month,
            week=week,
            date_val=date_val,
            date_start=date_start,
            date_end=date_end,
            iup_filter=iup_filter,
            alias="mp",
            date_field="date_production",
        )

        h_where, h_params = build_unit_date_filter_clause(
            filter_type=filter_type,
            year=year,
            month=month,
            week=week,
            date_val=date_val,
            date_start=date_start,
            date_end=date_end,
            iup_filter=iup_filter,
            alias="h",
            date_field="date",
        )

        f_iup_clause, f_iup_params = build_iup_clause(iup_filter, "f")

        query = f"""
            WITH prod_units AS (
                SELECT DISTINCT
                    mp.date_production AS date,
                    TRIM(mp.{production_unit_field}) AS unit_code
                FROM mining_productions mp
                WHERE {mp_where}
                    AND mp.{production_unit_field} IS NOT NULL
                    AND TRIM(mp.{production_unit_field}) <> ''
            )
            SELECT
                u.unit_code,
                TRIM(c.category) AS category,
                COALESCE(SUM(f.volume), 0) AS fuel,

                SUM(CASE WHEN s.code = 'EWH'
                    THEN COALESCE(d.duration_min, 0) ELSE 0 END) AS op,

                SUM(CASE WHEN s.code IN ('STB','SUPPORT','WX','SLP')
                    THEN COALESCE(d.duration_min, 0) ELSE 0 END) AS st,

                SUM(CASE WHEN s.code IN ('PM','BD')
                    THEN COALESCE(d.duration_min, 0) ELSE 0 END) AS mt,

                SUM(CASE WHEN s.code = 'BD'
                    THEN COALESCE(d.duration_min, 0) ELSE 0 END) AS bd,

                COUNT(DISTINCT h.date) * 1440 AS total_time,

                ROUND(
                    SUM(CASE WHEN s.code = 'EWH'
                        THEN COALESCE(d.duration_min, 0) ELSE 0 END)::numeric
                    /
                    NULLIF(
                        SUM(CASE WHEN s.code IN ('EWH','PM','BD')
                            THEN COALESCE(d.duration_min, 0) ELSE 0 END),
                        0
                    ) * 100,
                    2
                ) AS ma,

                ROUND(
                    SUM(CASE WHEN s.code IN ('EWH','STB','SUPPORT','WX','SLP')
                        THEN COALESCE(d.duration_min, 0) ELSE 0 END)::numeric
                    /
                    NULLIF((COUNT(DISTINCT h.date) * 1440), 0) * 100,
                    2
                ) AS pa,

                ROUND(
                    SUM(CASE WHEN s.code = 'EWH'
                        THEN COALESCE(d.duration_min, 0) ELSE 0 END)::numeric
                    /
                    NULLIF(
                        SUM(CASE WHEN s.code IN ('EWH','STB','SUPPORT','WX','SLP')
                            THEN COALESCE(d.duration_min, 0) ELSE 0 END),
                        0
                    ) * 100,
                    2
                ) AS ua,

                ROUND(
                    SUM(CASE WHEN s.code = 'EWH'
                        THEN COALESCE(d.duration_min, 0) ELSE 0 END)::numeric
                    /
                    NULLIF((COUNT(DISTINCT h.date) * 1440), 0) * 100,
                    2
                ) AS eu

            FROM mining_hm_unit h
            LEFT JOIN master_units u ON u.id = h.unit_id
            JOIN prod_units pu 
                ON pu.unit_code = TRIM(u.unit_code)
                AND pu.date = h.date
            LEFT JOIN mining_hm_unit_detail d ON d.hm_unit_id = h.id
            LEFT JOIN master_units_categories c ON c.id = u.id_category
            LEFT JOIN master_activity_categories s ON s.id = d.status_id
            LEFT JOIN mining_fuel_consumption f
                ON f.unit = u.unit_code
                AND f.date = h.date
                {f_iup_clause}
            WHERE {h_where}
            GROUP BY u.unit_code, c.category
            ORDER BY c.category, u.unit_code;
        """

        params = mp_params + f_iup_params + h_params

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        result = []

        for r in rows:
            result.append({
                "unit": r[0],
                "category": r[1],
                "fuel": float(r[2] or 0),
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
            "filter": {
                "filter_type": filter_type,
                "year": year,
                "month": month,
                "week": week,
                "date": date_val,
                "date_start": date_start,
                "date_end": date_end,
                "iup_id": iup_filter,
                "unit_type": unit_type,
            },
            "data": result,
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

def build_unit_date_filter_clause(
    filter_type=None,
    year=None,
    month=None,
    week=None,
    date_val=None,
    date_start=None,
    date_end=None,
    iup_filter=None,
    alias="mp",
    date_field="date_production",
):
    today = date.today()

    where_clause = "1=1"
    params = []

    iup_clause, iup_params = build_iup_clause(iup_filter, alias)
    where_clause += iup_clause
    params += iup_params

    date_col = f"{alias}.{date_field}"

    if filter_type == "daily" and date_val:
        where_clause += f" AND DATE({date_col}) = %s"
        params.append(date_val)

    elif filter_type == "weekly" and week:
        where_clause += f" AND TO_CHAR({date_col}, 'IYYY-IW') = %s"
        params.append(week)

    elif filter_type == "wtd" and week:
        iso_year, iso_week = parse_iso_week(week)
        start_of_week = date.fromisocalendar(iso_year, iso_week, 1)
        end_of_week = start_of_week + timedelta(days=6)
        end_of_wtd = min(today, end_of_week)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_week, end_of_wtd]

    elif filter_type == "monthly" and year and month:
        where_clause += f"""
            AND EXTRACT(YEAR FROM {date_col}) = %s
            AND EXTRACT(MONTH FROM {date_col}) = %s
        """
        params += [year, month]

    elif filter_type == "mtd" and year and month:
        start_of_month = date(int(year), int(month), 1)
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_of_month = date(int(year), int(month), last_day)
        end_of_mtd = min(today, end_of_month)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_month, end_of_mtd]

    elif filter_type == "yearly" and year:
        where_clause += f" AND EXTRACT(YEAR FROM {date_col}) = %s"
        params.append(year)

    elif filter_type == "ytd" and year:
        start_of_year = date(int(year), 1, 1)
        end_of_year = date(int(year), 12, 31)
        end_of_ytd = min(today, end_of_year)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_year, end_of_ytd]

    elif filter_type == "range" and date_start and date_end:
        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [date_start, date_end]

    return where_clause, params