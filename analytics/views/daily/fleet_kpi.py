# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
from datetime import datetime
from collections import defaultdict
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause

def min_to_hhmm(minutes):
    minutes = int(minutes or 0)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

# Kpi Daily Mining
def min_to_hour(m):
    return round((m or 0) / 60, 2)

def get_kpi_daily_hauler(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")

    try:
        datetime.strptime(filter_date, "%Y-%m-%d")
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    try:
        mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
        h_iup_clause, h_iup_params = build_iup_clause(iup_filter, "h")
        f_iup_clause, f_iup_params = build_iup_clause(iup_filter, "f")

        query = f"""
            WITH prod_units AS (
                SELECT DISTINCT
                    mp.date_production AS date,
                    TRIM(mp.hauler) AS unit_code
                FROM mining_productions mp
                WHERE mp.date_production = %s::date
                {mp_iup_clause}
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
                    (COUNT(DISTINCT h.date) * 1440) * 100,
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
                    (COUNT(DISTINCT h.date) * 1440) * 100,
                    2
                ) AS eu
            FROM mining_hm_unit h
            LEFT JOIN master_units u ON u.id = h.unit_id
            JOIN prod_units pu ON pu.unit_code = TRIM(u.unit_code) AND pu.date = h.date
            LEFT JOIN mining_hm_unit_detail d ON d.hm_unit_id = h.id
            LEFT JOIN master_units_categories c ON c.id = u.id_category
            LEFT JOIN master_activity_categories s ON s.id = d.status_id
            LEFT JOIN mining_fuel_consumption f
                ON f.unit = u.unit_code
                AND f.date = h.date
                {f_iup_clause}
            WHERE h.date = %s::date
            {h_iup_clause}
            GROUP BY u.unit_code, c.category
            ORDER BY c.category, u.unit_code;
        """

        params = [filter_date] + mp_iup_params + f_iup_params + [filter_date] + h_iup_params

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
            "data": result
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def get_kpi_daily_digger(request):
    filter_date = request.GET.get("filter_date")
    iup_filter = request.GET.get("iup_id")

    try:
        datetime.strptime(filter_date, "%Y-%m-%d")
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    try:
        mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
        h_iup_clause, h_iup_params = build_iup_clause(iup_filter, "h")
        f_iup_clause, f_iup_params = build_iup_clause(iup_filter, "f")

        query = f"""
            WITH prod_units AS (
                SELECT DISTINCT
                    mp.date_production AS date,
                    TRIM(mp.loader) AS unit_code
                FROM mining_productions mp
                WHERE mp.date_production = %s::date
                {mp_iup_clause}
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
                    (COUNT(DISTINCT h.date) * 1440) * 100,
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
                    (COUNT(DISTINCT h.date) * 1440) * 100,
                    2
                ) AS eu
            FROM mining_hm_unit h
            LEFT JOIN master_units u ON u.id = h.unit_id
            JOIN prod_units pu ON pu.unit_code = TRIM(u.unit_code) AND pu.date = h.date
            LEFT JOIN mining_hm_unit_detail d ON d.hm_unit_id = h.id
            LEFT JOIN master_units_categories c ON c.id = u.id_category
            LEFT JOIN master_activity_categories s ON s.id = d.status_id
            LEFT JOIN mining_fuel_consumption f
                ON f.unit = u.unit_code
                AND f.date = h.date
                {f_iup_clause}
            WHERE h.date = %s::date
            {h_iup_clause}
            GROUP BY u.unit_code, c.category
            ORDER BY c.category, u.unit_code;
        """

        params = [filter_date] + mp_iup_params + f_iup_params + [filter_date] + h_iup_params
        
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
            "data": result
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)