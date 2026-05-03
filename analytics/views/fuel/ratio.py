from datetime import date, timedelta
import calendar
import pandas as pd

from django.http import JsonResponse
from django.db import connection

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


def build_fuel_filter_clause(
    filter_type=None,
    year=None,
    month=None,
    week=None,
    date_val=None,
    date_start=None,
    date_end=None,
    iup_filter=None,
    alias="l",
):
    today = date.today()

    where_clause = "1=1"
    params = []

    iup_clause, iup_params = build_iup_clause(iup_filter, alias)
    where_clause += iup_clause
    params += iup_params

    date_col = f"{alias}.date_production"

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

def get_fuel_ratio(request):
    return summary_fuel_ratio(
        loader_view="view_mining_fuel_loader_all",
        hauler_view="view_mining_fuel_hauler_all",
        filter_type=request.GET.get("filter_type"),
        year=request.GET.get("year"),
        month=request.GET.get("month"),
        week=request.GET.get("week"),
        date_val=request.GET.get("filter_date") or request.GET.get("date"),
        date_start=request.GET.get("date_start"),
        date_end=request.GET.get("date_end"),
        iup_filter=request.GET.get("iup_id"),
    )

def get_fuel_ratio_ore(request):
    return summary_fuel_ratio(
        loader_view="view_mining_fuel_loader_ore",
        hauler_view="view_mining_fuel_hauler_ore",
        filter_type=request.GET.get("filter_type"),
        year=request.GET.get("year"),
        month=request.GET.get("month"),
        week=request.GET.get("week"),
        date_val=request.GET.get("filter_date") or request.GET.get("date"),
        date_start=request.GET.get("date_start"),
        date_end=request.GET.get("date_end"),
        iup_filter=request.GET.get("iup_id"),
    )

def summary_fuel_ratio(
    loader_view,
    hauler_view,
    filter_type=None,
    year=None,
    month=None,
    week=None,
    date_val=None,
    date_start=None,
    date_end=None,
    iup_filter=None,
):
    l_where, l_params = build_fuel_filter_clause(
        filter_type=filter_type,
        year=year,
        month=month,
        week=week,
        date_val=date_val,
        date_start=date_start,
        date_end=date_end,
        iup_filter=iup_filter,
        alias="l",
    )

    h_where, h_params = build_fuel_filter_clause(
        filter_type=filter_type,
        year=year,
        month=month,
        week=week,
        date_val=date_val,
        date_start=date_start,
        date_end=date_end,
        iup_filter=iup_filter,
        alias="h",
    )

    query = f"""
        WITH loader AS (
            SELECT
                l.date_production,
                SUM(COALESCE(l.total_loader, 0)) AS total_tonnage_loader,
                SUM(COALESCE(l.total_bcm, 0)) AS total_bcm_loader,
                SUM(COALESCE(l.total_fuel_loader, 0)) AS total_fuel_loader
            FROM {loader_view} l
            WHERE {l_where}
            GROUP BY l.date_production
        ),
        hauler AS (
            SELECT
                h.date_production,
                SUM(COALESCE(h.total_tonnage, 0)) AS total_tonnage_hauler,
                SUM(COALESCE(h.total_bcm, 0)) AS total_bcm_hauler,
                SUM(COALESCE(h.total_fuel_hauler, 0)) AS total_fuel_hauler
            FROM {hauler_view} h
            WHERE {h_where}
            GROUP BY h.date_production
        )
        SELECT
            COALESCE(h.date_production, l.date_production) AS date_production,
            COALESCE(h.total_tonnage_hauler, 0) + COALESCE(l.total_tonnage_loader, 0) AS total_tonnage,
            COALESCE(h.total_bcm_hauler, 0) + COALESCE(l.total_bcm_loader, 0) AS total_bcm,
            COALESCE(h.total_fuel_hauler, 0) + COALESCE(l.total_fuel_loader, 0) AS total_fuel,
            ROUND(
                (
                    COALESCE(h.total_fuel_hauler, 0) 
                    + COALESCE(l.total_fuel_loader, 0)
                )::numeric
                / NULLIF(
                    (
                        COALESCE(h.total_tonnage_hauler, 0) 
                        + COALESCE(l.total_tonnage_loader, 0)
                    )::numeric,
                    0
                ),
                3
            ) AS fuel_ratio_per_ton
        FROM hauler h
        FULL OUTER JOIN loader l
            ON h.date_production = l.date_production
        ORDER BY date_production;
    """

    params = l_params + h_params

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

    if df.empty:
        return JsonResponse({
            "filter": {
                "filter_type": filter_type,
                "year": year,
                "month": month,
                "week": week,
                "date": date_val,
                "date_start": date_start,
                "date_end": date_end,
                "iup_id": iup_filter,
            },
            "date_production": [],
            "total_tonnage": [],
            "total_bcm": [],
            "total_fuel": [],
            "fuel_ratio_per_ton": [],
            "summary": {
                "total_tonnage": 0,
                "total_bcm": 0,
                "total_fuel": 0,
                "fuel_ratio_per_ton": 0,
            },
        }, safe=False)

    numeric_cols = [
        "total_tonnage",
        "total_bcm",
        "total_fuel",
        "fuel_ratio_per_ton",
    ]

    df[numeric_cols] = df[numeric_cols].apply(
        pd.to_numeric,
        errors="coerce",
    ).fillna(0.0)

    total_tonnage = float(df["total_tonnage"].sum())
    total_bcm = float(df["total_bcm"].sum())
    total_fuel = float(df["total_fuel"].sum())

    fuel_ratio_per_ton = round(
        total_fuel / total_tonnage,
        3,
    ) if total_tonnage > 0 else 0

    return JsonResponse({
        "filter": {
            "filter_type": filter_type,
            "year": year,
            "month": month,
            "week": week,
            "date": date_val,
            "date_start": date_start,
            "date_end": date_end,
            "iup_id": iup_filter,
        },
        "date_production": df["date_production"].astype(str).tolist(),
        "total_tonnage": df["total_tonnage"].round(2).tolist(),
        "total_bcm": df["total_bcm"].round(2).tolist(),
        "total_fuel": df["total_fuel"].round(2).tolist(),
        "fuel_ratio_per_ton": df["fuel_ratio_per_ton"].round(3).tolist(),
        "summary": {
            "total_tonnage": round(total_tonnage, 2),
            "total_bcm": round(total_bcm, 2),
            "total_fuel": round(total_fuel, 2),
            "fuel_ratio_per_ton": fuel_ratio_per_ton,
        },
    }, safe=False)