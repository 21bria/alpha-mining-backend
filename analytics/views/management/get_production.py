from datetime import date, datetime, timedelta
import calendar
import logging

import pandas as pd
from django.db import connection, DatabaseError
from django.http import JsonResponse

from analytics.services.iup_filter import build_iup_clause

logger = logging.getLogger(__name__)


def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

def build_summary_filter_clause(
    filter_type="all",
    year=None,
    month=None,
    week=None,
    filter_date=None,
    period_start=None,
    period_end=None,
    iup_filter=None,
):
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    actual_iup_clause, actual_iup_params = build_iup_clause(iup_filter, "a")
    plan_iup_clause, plan_iup_params = build_iup_clause(iup_filter, "p")

    where_actual += actual_iup_clause
    where_plan += plan_iup_clause

    actual_params += actual_iup_params
    plan_params += plan_iup_params

    today = date.today()

    if filter_type == "daily":
        target_date = filter_date or today.isoformat()

        where_actual += " AND DATE(a.date_production) = %s"
        where_plan += " AND DATE(p.date_plan) = %s"

        actual_params.append(target_date)
        plan_params.append(target_date)

    elif filter_type == "weekly":
        if not week:
            raise ValueError("week wajib diisi untuk filter weekly")

        if "-" in str(week):
            iso_year, iso_week = map(int, str(week).split("-"))
        else:
            if not year:
                raise ValueError("year wajib diisi untuk filter weekly")

            iso_year = int(year)
            iso_week = int(week)

        start_date = date.fromisocalendar(iso_year, iso_week, 1)
        end_date = date.fromisocalendar(iso_year, iso_week, 7)

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "wtd":
        if not week:
            raise ValueError("week wajib diisi untuk filter wtd")

        if "-" in str(week):
            iso_year, iso_week = map(int, str(week).split("-"))
        else:
            if not year:
                raise ValueError("year wajib diisi untuk filter wtd")

            iso_year = int(year)
            iso_week = int(week)

        start_date = date.fromisocalendar(iso_year, iso_week, 1)
        week_end = date.fromisocalendar(iso_year, iso_week, 7)
        end_date = min(today, week_end)

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "monthly":
        year = int(year)
        month = int(month)

        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "mtd":
        year = int(year)
        month = int(month)

        start_date = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])
        end_date = min(today, month_end)

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "yearly":
        year = int(year)

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "ytd":
        year = int(year)

        start_date = date(year, 1, 1)
        year_end = date(year, 12, 31)
        end_date = min(today, year_end)

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "range":
        if not period_start or not period_end:
            raise ValueError("period_start dan period_end wajib diisi untuk filter range")

        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [period_start, period_end]
        plan_params += [period_start, period_end]

    elif filter_type == "all":
        pass

    else:
        raise ValueError(f"filter_type tidak valid: {filter_type}")

    return where_actual, where_plan, actual_params + plan_params

def get_summary_dataframe(where_actual, where_plan, params):
    query = f"""
        WITH actual AS (
            SELECT
                CASE
                    WHEN COALESCE(a.is_ore, false) = true THEN 'Ore'
                    ELSE 'Non Ore'
                END AS material_group,
                a.nama_material AS material_name,
                SUM(a.tonnage)::numeric AS actual
            FROM view_mining_productions a
            WHERE {where_actual}
              AND COALESCE(a.is_production, true) = true
            GROUP BY
                CASE
                    WHEN COALESCE(a.is_ore, false) = true THEN 'Ore'
                    ELSE 'Non Ore'
                END,
                a.nama_material
        ),

        plan AS (
            SELECT
                CASE
                    WHEN COALESCE(p.is_ore, false) = true THEN 'Ore'
                    ELSE 'Non Ore'
                END AS material_group,
                p.material_name AS material_name,
                SUM(p.tonnage)::numeric AS plan
            FROM view_mining_plan_productions p
            WHERE {where_plan}
              AND COALESCE(p.is_production, true) = true
            GROUP BY
                CASE
                    WHEN COALESCE(p.is_ore, false) = true THEN 'Ore'
                    ELSE 'Non Ore'
                END,
                p.material_name
        )

        SELECT
            COALESCE(a.material_group, p.material_group) AS material_group,
            COALESCE(a.material_name, p.material_name) AS material_name,
            ROUND(COALESCE(a.actual, 0), 2) AS actual,
            ROUND(COALESCE(p.plan, 0), 2) AS plan
        FROM actual a
        FULL OUTER JOIN plan p
            ON LOWER(TRIM(COALESCE(a.material_group, ''))) =
               LOWER(TRIM(COALESCE(p.material_group, '')))
            AND LOWER(TRIM(COALESCE(a.material_name, ''))) =
                LOWER(TRIM(COALESCE(p.material_name, '')))
        ORDER BY
            material_group,
            material_name
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    return pd.DataFrame(
        data,
        columns=[
            "material_group",
            "material_name",
            "actual",
            "plan",
        ],
    )


def generate_summary(df, label):
    if df.empty:
        return {
            "label": label,
            "ore_materials": [],
            "non_ore_materials": [],
            "other_materials": [],
            "total_ore": 0.0,
            "total_ore_plan": 0.0,
            "achievement_ore": 0.0,
            "total_non_ore": 0.0,
            "total_non_ore_plan": 0.0,
            "achievement_non_ore": 0.0,
            "total_actual": 0.0,
            "total_plan": 0.0,
            "achievement": 0.0,
        }

    df["actual"] = pd.to_numeric(df["actual"], errors="coerce").fillna(0.0)
    df["plan"] = pd.to_numeric(df["plan"], errors="coerce").fillna(0.0)

    df["material_group_norm"] = (
        df["material_group"]
        .fillna("Other")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    def safe_div(a, b):
        return round((a / b * 100), 0) if b > 0 else 0

    def build_materials(group_key):
        group_df = df[df["material_group_norm"] == group_key].copy()

        return [
            {
                "material": row["material_name"],
                "actual": float(round(row["actual"], 2)),
                "plan": float(round(row["plan"], 2)),
                "achievement": float(safe_div(row["actual"], row["plan"])),
            }
            for _, row in group_df.iterrows()
        ]

    ore_df = df[df["material_group_norm"] == "ore"]
    non_ore_df = df[df["material_group_norm"] == "non ore"]
    other_df = df[
        ~df["material_group_norm"].isin(["ore", "non ore"])
    ]

    total_ore = float(round(ore_df["actual"].sum(), 2))
    total_ore_plan = float(round(ore_df["plan"].sum(), 2))

    total_non_ore = float(round(non_ore_df["actual"].sum(), 2))
    total_non_ore_plan = float(round(non_ore_df["plan"].sum(), 2))

    total_other = float(round(other_df["actual"].sum(), 2))
    total_other_plan = float(round(other_df["plan"].sum(), 2))

    total_actual = float(round(df["actual"].sum(), 2))
    total_plan = float(round(df["plan"].sum(), 2))

    other_materials = []
    for _, row in other_df.iterrows():
        actual = float(round(row["actual"], 2))
        plan = float(round(row["plan"], 2))

        other_materials.append({
            "group": row["material_group"],
            "material": row["material_name"],
            "actual": actual,
            "plan": plan,
            "achievement": float(safe_div(actual, plan)),
        })

    return {
        "label": label,

        "ore_materials": build_materials("ore"),
        "non_ore_materials": build_materials("non ore"),
        "other_materials": other_materials,

        "total_ore": total_ore,
        "total_ore_plan": total_ore_plan,
        "achievement_ore": float(safe_div(total_ore, total_ore_plan)),

        "total_non_ore": total_non_ore,
        "total_non_ore_plan": total_non_ore_plan,
        "achievement_non_ore": float(safe_div(total_non_ore, total_non_ore_plan)),

        "total_other": total_other,
        "total_other_plan": total_other_plan,
        "achievement_other": float(safe_div(total_other, total_other_plan)),

        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": float(safe_div(total_actual, total_plan)),
    }


def get_summary_management(request):
    try:
        iup_filter  = request.GET.get("iup_id")
        filter_type = request.GET.get("filter_type")
        filter_year = (
            request.GET.get("yearly")
            or request.GET.get("year")
        )

        filter_month = (
            request.GET.get("monthly")
            or request.GET.get("month")
        )

        filter_week = (
            request.GET.get("weekly")
            or request.GET.get("week")
        )
        filter_date = request.GET.get("filter_date")

        period_start = (
            request.GET.get("period_start")
            or request.GET.get("date_start")
        )
        period_end = (
            request.GET.get("period_end")
            or request.GET.get("date_end")
        )

        result = {}

        if filter_type == "monthly":
            wa, wp, params = build_summary_filter_clause(
                "monthly",
                year=filter_year,
                month=filter_month,
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["monthly"] = generate_summary(df, "MONTHLY")

            wa, wp, params = build_summary_filter_clause(
                "mtd",
                year=filter_year,
                month=filter_month,
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["mtd"] = generate_summary(df, "MTD")

        elif filter_type == "weekly":
            wa, wp, params = build_summary_filter_clause(
                "weekly",
                year=filter_year,
                week=filter_week,
                iup_filter=iup_filter,
            )

            df = get_summary_dataframe(wa, wp, params)
            result["weekly"] = generate_summary(df, "WEEKLY")

            wa, wp, params = build_summary_filter_clause(
                "wtd",
                year=filter_year,
                week=filter_week,
                iup_filter=iup_filter,
            )

            df = get_summary_dataframe(wa, wp, params)
            result["wtd"] = generate_summary(df, "WTD")

        elif filter_type == "yearly":
            wa, wp, params = build_summary_filter_clause(
                "yearly",
                year=filter_year,
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["yearly"] = generate_summary(df, "YEARLY")

            wa, wp, params = build_summary_filter_clause(
                "ytd",
                year=filter_year,
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["ytd"] = generate_summary(df, "YTD")

        elif filter_type == "range":
            wa, wp, params = build_summary_filter_clause(
                "range",
                period_start=period_start,
                period_end=period_end,
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["range"] = generate_summary(df, "RANGE")

        elif filter_type == "daily":
            wa, wp, params = build_summary_filter_clause(
                "daily",
                filter_date=filter_date,
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["daily"] = generate_summary(df, "DAILY")

        else:
            wa, wp, params = build_summary_filter_clause(
                "all",
                iup_filter=iup_filter,
            )
            df = get_summary_dataframe(wa, wp, params)
            result["all"] = generate_summary(df, "ALL")

        return JsonResponse(result, safe=False)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    except DatabaseError as e:
        logger.error(f"Database query failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)