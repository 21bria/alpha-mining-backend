# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
from datetime import datetime
from collections import defaultdict
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause

# Fuel Daily Report
def get_fuel_daily_report(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    data = fuel_daily_report(filter_date, iup_filter)
    return JsonResponse(data, safe=False)

def fuel_daily_report(filter_date, iup_filter=None):
    mf_iup_clause, mf_iup_params = build_iup_clause(iup_filter, "mf")

    query = f"""
        SELECT 
            mf.shift,
            SUM(COALESCE(mf.volume, 0)) AS total_fuel
        FROM mining_fuel_consumption mf
        WHERE mf.date = %s::date
        {mf_iup_clause}
        GROUP BY mf.shift
        ORDER BY mf.shift;
    """

    params = [filter_date] + mf_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    by_shift = []
    grand_total = 0

    for shift, total_fuel in rows:
        fuel = float(total_fuel or 0)
        grand_total += fuel

        by_shift.append({
            "shift": shift,
            "total_fuel": fuel
        })

    return {
        "by_shift": by_shift,
        "grand_total": round(grand_total, 2)
    }

def get_daily_fuel_ratio(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    return summary_daily_fuel_ratio(filter_date, iup_filter)


def summary_daily_fuel_ratio(filter_date, iup_filter=None):
    l_iup_clause, l_iup_params = build_iup_clause(iup_filter, "l")
    h_iup_clause, h_iup_params = build_iup_clause(iup_filter, "h")

    query = f"""
        WITH loader AS (
            SELECT
                l.date_production,
                SUM(l.total_loader) AS total_tonnage_loader,
                SUM(l.total_bcm) AS total_bcm_loader,
                SUM(l.total_fuel_loader) AS total_fuel_loader
            FROM view_mining_fuel_loader_all l
            WHERE l.date_production = %s::date
            {l_iup_clause}
            GROUP BY l.date_production
        ),
        hauler AS (
            SELECT
                h.date_production,
                SUM(h.total_tonnage) AS total_tonnage_hauler,
                SUM(h.total_bcm) AS total_bcm_hauler,
                SUM(h.total_fuel_hauler) AS total_fuel_hauler
            FROM view_mining_fuel_hauler_all h
            WHERE h.date_production = %s::date
            {h_iup_clause}
            GROUP BY h.date_production
        )
        SELECT
            COALESCE(h.date_production, l.date_production) AS date_production,
            COALESCE(h.total_tonnage_hauler, 0) + COALESCE(l.total_tonnage_loader, 0) AS total_tonnage,
            COALESCE(h.total_bcm_hauler, 0) + COALESCE(l.total_bcm_loader, 0) AS total_bcm,
            COALESCE(h.total_fuel_hauler, 0) + COALESCE(l.total_fuel_loader, 0) AS total_fuel,
            ROUND(
                (COALESCE(h.total_fuel_hauler, 0) + COALESCE(l.total_fuel_loader, 0))::numeric
                / NULLIF((COALESCE(h.total_tonnage_hauler, 0) + COALESCE(l.total_tonnage_loader, 0))::numeric, 0),
                3
            ) AS fuel_ratio_per_ton
        FROM hauler h
        FULL OUTER JOIN loader l
            ON h.date_production = l.date_production
        ORDER BY date_production;
    """

    params = [filter_date] + l_iup_params + [filter_date] + h_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "date_production",
            "total_tonnage",
            "total_bcm",
            "total_fuel",
            "fuel_ratio_per_ton",
        ],
    )

    numeric_cols = ["total_tonnage", "total_bcm", "total_fuel", "fuel_ratio_per_ton"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    return JsonResponse({
        "date_production": df["date_production"].tolist(),
        "total_tonnage": df["total_tonnage"].tolist(),
        "total_bcm": df["total_bcm"].tolist(),
        "total_fuel": df["total_fuel"].tolist(),
        "fuel_ratio_per_ton": df["fuel_ratio_per_ton"].tolist(),
    }, safe=False)

def get_daily_fuel_ratio_ore(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    return summary_daily_fuel_ratio_ore(filter_date, iup_filter)


def summary_daily_fuel_ratio_ore(filter_date, iup_filter=None):
    l_iup_clause, l_iup_params = build_iup_clause(iup_filter, "l")
    h_iup_clause, h_iup_params = build_iup_clause(iup_filter, "h")

    query = f"""
        WITH loader AS (
            SELECT
                l.date_production,
                SUM(l.total_loader) AS total_tonnage_loader,
                SUM(l.total_bcm) AS total_bcm_loader,
                SUM(l.total_fuel_loader) AS total_fuel_loader
            FROM view_mining_fuel_loader_ore l
            WHERE l.date_production = %s::date
            {l_iup_clause}
            GROUP BY l.date_production
        ),
        hauler AS (
            SELECT
                h.date_production,
                SUM(h.total_tonnage) AS total_tonnage_hauler,
                SUM(h.total_bcm) AS total_bcm_hauler,
                SUM(h.total_fuel_hauler) AS total_fuel_hauler
            FROM view_mining_fuel_hauler_ore h
            WHERE h.date_production = %s::date
            {h_iup_clause}
            GROUP BY h.date_production
        )
        SELECT
            COALESCE(h.date_production, l.date_production) AS date_production,
            COALESCE(h.total_tonnage_hauler, 0) + COALESCE(l.total_tonnage_loader, 0) AS total_tonnage,
            COALESCE(h.total_bcm_hauler, 0) + COALESCE(l.total_bcm_loader, 0) AS total_bcm,
            COALESCE(h.total_fuel_hauler, 0) + COALESCE(l.total_fuel_loader, 0) AS total_fuel,
            ROUND(
                (COALESCE(h.total_fuel_hauler, 0) + COALESCE(l.total_fuel_loader, 0))::numeric
                / NULLIF((COALESCE(h.total_tonnage_hauler, 0) + COALESCE(l.total_tonnage_loader, 0))::numeric, 0),
                3
            ) AS fuel_ratio_per_ton
        FROM hauler h
        FULL OUTER JOIN loader l
            ON h.date_production = l.date_production
        ORDER BY date_production;
    """

    params = [filter_date] + l_iup_params + [filter_date] + h_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "date_production",
            "total_tonnage",
            "total_bcm",
            "total_fuel",
            "fuel_ratio_per_ton",
        ],
    )

    numeric_cols = ["total_tonnage", "total_bcm", "total_fuel", "fuel_ratio_per_ton"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    return JsonResponse({
        "date_production": df["date_production"].tolist(),
        "total_tonnage": df["total_tonnage"].tolist(),
        "total_bcm": df["total_bcm"].tolist(),
        "total_fuel": df["total_fuel"].tolist(),
        "fuel_ratio_per_ton": df["fuel_ratio_per_ton"].tolist(),
    }, safe=False)