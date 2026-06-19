# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from django.utils.timezone import now
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause

def parse_iso_week(week_value):
    iso_year_str, iso_week_str = str(week_value).split("-")
    return int(iso_year_str), int(iso_week_str)

def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

def summary_ore(request):
    try:

        query = """
                SELECT 
                    SUM(CASE WHEN nama_material IN ('LGLO', 'MGLO', 'HGLO','LGSO', 'MGSO', 'HGSO','LIM','SAP') THEN tonnage ELSE 0 END)::numeric  AS total,
                    SUM(CASE WHEN nama_material IN ('LGLO', 'MGLO', 'HGLO','LIM') THEN tonnage ELSE 0 END)::numeric AS limonite,
                    SUM(CASE WHEN nama_material IN ('LGSO', 'MGSO', 'HGSO','SAP') THEN tonnage ELSE 0 END)::numeric AS saprolite
                FROM view_mining_productions
                """
 
        # Use the correct database connection
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()

        total_ore = [entry[0] for entry in data]
        data_hpal = [entry[1] for entry in data]
        data_rkef = [entry[2] for entry in data]

        return JsonResponse({
            'data_hpal': data_hpal,
            'data_rkef': data_rkef,
            'total_ore': total_ore,
        })

    except DatabaseError as e:
        logger.error(f"Database query failed: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
      
def summary_mines(request):
    try:
        query = """
               SELECT 
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "TopSoil",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Waste",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "OB",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Quarry",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Ballast",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Biomass"
                FROM view_mining_productions
                """

        # Use the correct database connection
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()

        data_topsoil = [entry[0] for entry in data]
        data_waste   = [entry[1] for entry in data]
        data_ob      = [entry[2] for entry in data]
        data_quarry  = [entry[3] for entry in data]
        data_ballast = [entry[4] for entry in data]
        data_biomass = [entry[5] for entry in data]

        # Tambahkan data_orders: jumlahkan  ob + quarry + ballast + biomass
        data_orders = [entry[2] + entry[3] + entry[4] + entry[5] for entry in data]

        return JsonResponse({
            'data_topsoil'  : data_topsoil,
            'data_waste'    : data_waste,
            'data_ob'       : data_ob,
            'data_ballast'  : data_ballast,
            'data_quarry'   : data_quarry,
            'data_biomass'  : data_biomass,
            'data_orders'   : data_orders,
        })
    except DatabaseError as e:
        logger.error(f"Database query failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)    

def build_filter_clause(
    filter_type,
    year,
    month,
    week,
    date_val,
    date_start,
    date_end,
    iup_filter=None,
):
    today = date.today()

    # pakai alias karena nanti query actual = view_mining_productions a
    # dan plan = mining_plan_productions p
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    # FILTER IUP
    actual_iup_clause, actual_iup_params = build_iup_clause(iup_filter, "a")
    plan_iup_clause, plan_iup_params = build_iup_clause(iup_filter, "p")

    where_actual += actual_iup_clause
    where_plan += plan_iup_clause

    actual_params += actual_iup_params
    plan_params += plan_iup_params

    if filter_type == "daily" and date_val:
        group_actual = "DATE(a.date_production)"
        group_plan = "DATE(p.date_plan)"

        where_actual += " AND DATE(a.date_production) = %s"
        where_plan += " AND DATE(p.date_plan) = %s"

        actual_params.append(date_val)
        plan_params.append(date_val)

    elif filter_type == "weekly" and week:
        group_actual = "TO_CHAR(a.date_production, 'IYYY-IW')"
        group_plan = "TO_CHAR(p.date_plan, 'IYYY-IW')"

        where_actual += " AND TO_CHAR(a.date_production, 'IYYY-IW') = %s"
        where_plan += " AND TO_CHAR(p.date_plan, 'IYYY-IW') = %s"

        actual_params.append(week)
        plan_params.append(week)

    elif filter_type == "wtd" and week:
        group_actual = "DATE(a.date_production)"
        group_plan = "DATE(p.date_plan)"

        iso_year, iso_week = parse_iso_week(week)

        start_of_week = date.fromisocalendar(iso_year, iso_week, 1)
        end_of_week = start_of_week + timedelta(days=6)
        end_of_wtd = min(today, end_of_week)

        where_actual += " AND a.date_production BETWEEN %s AND %s"
        where_plan += " AND p.date_plan BETWEEN %s AND %s"

        actual_params += [start_of_week, end_of_wtd]
        plan_params += [start_of_week, end_of_wtd]

    elif filter_type == "monthly" and year and month:
        group_actual = "TO_CHAR(a.date_production, 'YYYY-MM')"
        group_plan = "TO_CHAR(p.date_plan, 'YYYY-MM')"

        where_actual += """
            AND EXTRACT(YEAR FROM a.date_production) = %s
            AND EXTRACT(MONTH FROM a.date_production) = %s
        """
        where_plan += """
            AND EXTRACT(YEAR FROM p.date_plan) = %s
            AND EXTRACT(MONTH FROM p.date_plan) = %s
        """

        actual_params += [year, month]
        plan_params += [year, month]

    elif filter_type == "mtd" and year and month:
        start_of_month = date(int(year), int(month), 1)
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_of_month = date(int(year), int(month), last_day)
        end_of_mtd = min(today, end_of_month)

        group_actual = "DATE(a.date_production)"
        group_plan = "DATE(p.date_plan)"

        where_actual += " AND a.date_production BETWEEN %s AND %s"
        where_plan += " AND p.date_plan BETWEEN %s AND %s"

        actual_params += [start_of_month, end_of_mtd]
        plan_params += [start_of_month, end_of_mtd]

    elif filter_type == "yearly" and year:
        group_actual = "EXTRACT(YEAR FROM a.date_production)::int"
        group_plan = "EXTRACT(YEAR FROM p.date_plan)::int"

        where_actual += " AND EXTRACT(YEAR FROM a.date_production) = %s"
        where_plan += " AND EXTRACT(YEAR FROM p.date_plan) = %s"

        actual_params.append(year)
        plan_params.append(year)

    elif filter_type == "ytd" and year:
        start_of_year = date(int(year), 1, 1)
        end_of_year = date(int(year), 12, 31)
        end_of_ytd = min(today, end_of_year)

        group_actual = "DATE(a.date_production)"
        group_plan = "DATE(p.date_plan)"

        where_actual += " AND a.date_production BETWEEN %s AND %s"
        where_plan += " AND p.date_plan BETWEEN %s AND %s"

        actual_params += [start_of_year, end_of_ytd]
        plan_params += [start_of_year, end_of_ytd]

    elif filter_type == "range" and date_start and date_end:
        group_actual = "DATE(a.date_production)"
        group_plan = "DATE(p.date_plan)"

        where_actual += " AND a.date_production BETWEEN %s AND %s"
        where_plan += " AND p.date_plan BETWEEN %s AND %s"

        actual_params += [date_start, date_end]
        plan_params += [date_start, date_end]

    else:
        group_actual = "EXTRACT(YEAR FROM a.date_production)::int"
        group_plan = "EXTRACT(YEAR FROM p.date_plan)::int"

    params = actual_params + plan_params
    return where_actual, where_plan, group_actual, group_plan, params

def get_summary_dataframe(where_actual, where_plan, group_actual, group_plan, params):
    query = f"""
        WITH actual AS (
            SELECT
                {group_actual} AS periode,

                SUM(
                    CASE
                        WHEN COALESCE(a.is_ore, false) = true
                         AND COALESCE(a.is_production, true) = true
                        THEN a.tonnage ELSE 0
                    END
                )::numeric AS ore,

                SUM(
                    CASE
                        WHEN COALESCE(a.is_ore, false) = false
                         AND COALESCE(a.is_production, true) = true
                        THEN a.tonnage ELSE 0
                    END
                )::numeric AS non_ore

            FROM view_mining_productions a
            WHERE {where_actual}
            GROUP BY {group_actual}
        ),

        plan AS (
            SELECT
                {group_plan} AS periode,

                SUM(
                    CASE
                        WHEN COALESCE(p.is_ore, false) = true
                         AND COALESCE(p.is_production, true) = true
                        THEN p.tonnage ELSE 0
                    END
                )::numeric AS ore_plan,

                SUM(
                    CASE
                        WHEN COALESCE(p.is_ore, false) = false
                         AND COALESCE(p.is_production, true) = true
                        THEN p.tonnage ELSE 0
                    END
                )::numeric AS non_ore_plan

            FROM view_mining_plan_productions p
            WHERE {where_plan}
            GROUP BY {group_plan}
        )

        SELECT
            COALESCE(a.periode, p.periode) AS periode,
            ROUND(COALESCE(a.ore, 0), 2) AS ore,
            ROUND(COALESCE(p.ore_plan, 0), 2) AS ore_plan,
            ROUND(COALESCE(a.non_ore, 0), 2) AS non_ore,
            ROUND(COALESCE(p.non_ore_plan, 0), 2) AS non_ore_plan
        FROM actual a
        FULL OUTER JOIN plan p
            ON a.periode = p.periode
        ORDER BY periode
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=[
        "periode",
        "ore",
        "ore_plan",
        "non_ore",
        "non_ore_plan",
    ])

    return df

def generate_summary(df, label):
    df["total_ore"] = df["ore"]
    df["total_ore_plan"] = df["ore_plan"]

    df["total_non_ore"] = df["non_ore"]
    df["total_non_ore_plan"] = df["non_ore_plan"]

    df["total_actual"] = df["total_ore"] + df["total_non_ore"]
    df["total_plan"] = df["total_ore_plan"] + df["total_non_ore_plan"]

    def safe_div(a, b):
        return round((a / b * 100), 0) if b > 0 else 0

    return {
        "label": label,

        "total_ore": float(round(df["total_ore"].sum(), 2)),
        "total_ore_plan": float(round(df["total_ore_plan"].sum(), 2)),

        "total_non_ore": float(round(df["total_non_ore"].sum(), 2)),
        "total_non_ore_plan": float(round(df["total_non_ore_plan"].sum(), 2)),

        "total_actual": float(round(df["total_actual"].sum(), 2)),
        "total_plan": float(round(df["total_plan"].sum(), 2)),

        "achievement": float(safe_div(df["total_actual"].sum(), df["total_plan"].sum())),
        "achievement_ore": float(safe_div(df["total_ore"].sum(), df["total_ore_plan"].sum())),
        "achievement_non_ore": float(safe_div(df["total_non_ore"].sum(), df["total_non_ore_plan"].sum())),
    }

def get_summary_mines(request):
    iup_filter   = request.GET.get("iup_id")
    filter_type  = request.GET.get("filter_type", "all")
    filter_year  = int(request.GET.get("year", 0))
    filter_month = int(request.GET.get("month", 0))
    filter_week  = request.GET.get("week")
    filter_date  = request.GET.get("filter_date")
    date_start   = request.GET.get("date_start")
    date_end     = request.GET.get("date_end")

    result = {}

    if filter_type == "monthly":
        wa1, wp1, ga1, gp1, param1 = build_filter_clause(
            "monthly", filter_year, filter_month, None, None, None, None, iup_filter
        )
        df_monthly = get_summary_dataframe(wa1, wp1, ga1, gp1, param1)
        result["monthly"] = generate_summary(df_monthly, "MONTHLY")

        wa2, wp2, ga2, gp2, param2 = build_filter_clause(
            "mtd", filter_year, filter_month, None, None, None, None, iup_filter
        )
        df_mtd = get_summary_dataframe(wa2, wp2, ga2, gp2, param2)
        result["mtd"] = generate_summary(df_mtd, "MTD")

    elif filter_type == "weekly":
        wa1, wp1, ga1, gp1, param1 = build_filter_clause(
            "weekly", filter_year, filter_month, filter_week, None, None, None, iup_filter
        )
        df_weekly = get_summary_dataframe(wa1, wp1, ga1, gp1, param1)
        result["weekly"] = generate_summary(df_weekly, "WEEKLY")

        wa2, wp2, ga2, gp2, param2 = build_filter_clause(
            "wtd", filter_year, filter_month, filter_week, None, None, None, iup_filter
        )
        df_wtd = get_summary_dataframe(wa2, wp2, ga2, gp2, param2)
        result["wtd"] = generate_summary(df_wtd, "WTD")

    elif filter_type == "yearly":
        wa1, wp1, ga1, gp1, param1 = build_filter_clause(
            "yearly", filter_year, None, None, None, None, None, iup_filter
        )
        df_yearly = get_summary_dataframe(wa1, wp1, ga1, gp1, param1)
        result["yearly"] = generate_summary(df_yearly, "YEARLY")

        wa2, wp2, ga2, gp2, param2 = build_filter_clause(
            "ytd", filter_year, None, None, None, None, None, iup_filter
        )
        df_ytd = get_summary_dataframe(wa2, wp2, ga2, gp2, param2)
        result["ytd"] = generate_summary(df_ytd, "YTD")

    elif filter_type == "range":
        wa, wp, ga, gp, params = build_filter_clause(
            "range", None, None, None, None, date_start, date_end, iup_filter
        )
        df_range = get_summary_dataframe(wa, wp, ga, gp, params)
        result["range"] = generate_summary(df_range, "RANGE")

    elif filter_type == "daily":
        wa, wp, ga, gp, params = build_filter_clause(
            "daily", None, None, None, filter_date, None, None, iup_filter
        )
        df_daily = get_summary_dataframe(wa, wp, ga, gp, params)
        result["daily"] = generate_summary(df_daily, "DAILY")

    else:
        wa, wp, ga, gp, params = build_filter_clause(
            "all", None, None, None, None, None, None, iup_filter
        )
        df_all = get_summary_dataframe(wa, wp, ga, gp, params)
        result["all"] = generate_summary(df_all, "ALL")

    return JsonResponse(result, safe=False)

# For Chart
def get_chart_mining(request):
    iup_filter   = request.GET.get("iup_id")
    filter_type  = request.GET.get("filter_type")
    filter_year  = int(request.GET.get("year", 0))
    filter_month = int(request.GET.get("month", 0))
    filter_week  = request.GET.get("week")
    filter_date  = request.GET.get("filter_date")
    date_start   = request.GET.get("date_start")
    date_end     = request.GET.get("date_end")

    if filter_type == "monthly" and filter_year and filter_month:
        return get_monthly_chart(filter_year, filter_month, iup_filter)

    elif filter_type == "daily" and filter_date:
        return get_daily_chart(filter_date, iup_filter)

    elif filter_type == "range" and date_start and date_end:
        return get_range_chart(date_start, date_end, iup_filter)

    elif filter_type == "yearly" and filter_year:
        return get_yearly_chart(filter_year, iup_filter)

    elif filter_type == "weekly" and filter_week:
        return get_weekly_chart(filter_week, iup_filter)

    elif filter_type == "all":
        return get_all_chart(iup_filter)

    else:
        return JsonResponse({"error": "Invalid filter"}, status=400)

def get_daily_chart(filter_date, iup_filter=None):
    where_actual = "mp.date_production = %s::date"
    where_plan = "p.date_plan = %s::date"

    actual_params = [filter_date]
    plan_params = [filter_date]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND mp.iup_id IN ({placeholders})"
            where_plan += f" AND p.iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH working_hours AS (
            SELECT
                hour_label,
                CASE
                    WHEN hour_label >= 7 THEN hour_label
                    ELSE hour_label + 24
                END AS sort_order
            FROM generate_series(0, 23) AS hour_label
        ),

        hour_series AS (
            SELECT 
                make_time(hour_label, 0, 0) AS raw_time,
                TO_CHAR(make_time(hour_label, 0, 0), 'HH24') AS left_time,
                hour_label,
                sort_order
            FROM working_hours
        ),

        agg_data AS (
            SELECT 
                LPAD(mp.t_load::text, 2, '0') AS t_load_time,
                SUM(mp.tonnage) AS total_tonnage
            FROM view_mining_productions mp
            WHERE {where_actual}
            AND COALESCE(mp.is_production, true) = true
            GROUP BY LPAD(mp.t_load::text, 2, '0')
        ),

        plan_per_hour AS (
            SELECT
                ROUND(
                    (COALESCE(SUM(p.tonnage), 0) / 22)::numeric,
                    2
                ) AS plan_data
            FROM view_mining_plan_productions p
            WHERE {where_plan}
            AND COALESCE(p.is_production, true) = true
        )

        SELECT
            hs.hour_label AS id,
            hs.left_time,
            COALESCE(a.total_tonnage, 0)::numeric(10,2) AS total,
            COALESCE(p.plan_data, 0)::numeric(10,2) AS plan_data
        FROM hour_series hs
        LEFT JOIN agg_data a
            ON hs.left_time = a.t_load_time
        CROSS JOIN plan_per_hour p
        ORDER BY hs.sort_order;
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=["time", "left_time", "total", "plan_data"],
    )

    df["total"] = (
        pd.to_numeric(df["total"], errors="coerce")
        .fillna(0.0)
        .round(2)
    )

    df["plan_data"] = (
        pd.to_numeric(df["plan_data"], errors="coerce")
        .fillna(0.0)
        .round(2)
    )

    df["achievement"] = df.apply(
        lambda r: round((r["total"] / r["plan_data"] * 100), 2)
        if r["plan_data"] > 0
        else 0.0,
        axis=1,
    )

    return JsonResponse(
        {
            "x_data": df["left_time"].tolist(),
            "total_actual": df["total"].tolist(),
            "total_plan": df["plan_data"].tolist(),
            "achievement": df["achievement"].tolist(),
        },
        safe=False,
    )

def get_chart_ore_quality(request):
    iup_filter   = request.GET.get("iup_id")
    filter_type  = request.GET.get("filter_type")
    filter_date  = request.GET.get("filter_date")

    if filter_type == "daily" and filter_date:
        return get_daily_ore_chart(filter_date, iup_filter)

    return JsonResponse({"error": "Invalid filter"}, status=400)

def get_daily_ore_chart(filter_date, iup_filter=None):
    where_actual = """
        mp.date_production = %s::date
        AND COALESCE(mp.is_ore, false) = true
        AND COALESCE(mp.is_production, true) = true
    """

    where_plan = """
        p.date_plan = %s::date
        AND COALESCE(p.is_ore, false) = true
        AND COALESCE(p.is_production, true) = true
    """

    actual_params = [filter_date]
    plan_params = [filter_date]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND mp.iup_id IN ({placeholders})"
            where_plan += f" AND p.iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH working_hours AS (
            SELECT
                hour_label,
                CASE
                    WHEN hour_label >= 7 THEN hour_label
                    ELSE hour_label + 24
                END AS sort_order
            FROM generate_series(0, 23) AS hour_label
        ),

        hour_series AS (
            SELECT 
                make_time(hour_label, 0, 0) AS raw_time,
                TO_CHAR(make_time(hour_label, 0, 0), 'HH24') AS left_time,
                hour_label,
                sort_order
            FROM working_hours
        ),

        agg_actual AS (
            SELECT 
                TO_CHAR(make_time(mp.t_load::int, 0, 0), 'HH24') AS t_load_time,
                SUM(mp.tonnage) AS total_tonnage
            FROM view_mining_productions mp
            WHERE {where_actual}
            GROUP BY mp.t_load
        ),

        agg_plan AS (
            SELECT 
                ROUND(
                    (COALESCE(SUM(p.tonnage), 0) / 22)::numeric,
                    2
                ) AS plan_data
            FROM view_mining_plan_productions p
            WHERE {where_plan}
        )

        SELECT
            hs.hour_label AS id,
            hs.left_time,
            COALESCE(a.total_tonnage, 0)::numeric(10,2) AS total,
            COALESCE(p.plan_data, 0)::numeric(10,2) AS plan_data
        FROM hour_series hs
        LEFT JOIN agg_actual a
            ON hs.left_time = a.t_load_time
        CROSS JOIN agg_plan p
        ORDER BY hs.sort_order;
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=["time", "left_time", "total", "plan_data"])
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0).round(2)
    df["plan_data"] = pd.to_numeric(df["plan_data"], errors="coerce").fillna(0.0).round(2)

    df["achievement"] = df.apply(
        lambda r: round((r["total"] / r["plan_data"] * 100), 2)
        if r["plan_data"] > 0
        else 0.0,
        axis=1,
    )

    return JsonResponse(
        {
            "x_data": df["left_time"].tolist(),
            "total_actual": df["total"].tolist(),
            "total_plan": df["plan_data"].tolist(),
            "achievement": df["achievement"].tolist(),
        },
        safe=False,
    )

# http://kawi.localhost:8000/api/analytics/raw/mining/chart/?filter_type=monthly&filter_year=2026&filter_month=3&iup_id=1
def get_monthly_chart(filter_year, filter_month, iup_filter=None):
    year = int(filter_year)
    month = int(filter_month)

    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [tgl_pertama, tgl_terakhir]
    plan_params = [tgl_pertama, tgl_terakhir]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    params = [
        tgl_pertama, tgl_terakhir,
        *actual_params,
        *plan_params,
    ]

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
        ),
        actual AS (
            SELECT
                date_production::date AS date,
                SUM(tonnage) AS tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            AND COALESCE(is_production, true) = true
            GROUP BY date_production::date
        ),
        plan AS (
            SELECT 
                date_plan::date AS date,
                SUM(tonnage) AS plan_data
            FROM view_mining_plan_productions
            WHERE {where_plan}
            AND COALESCE(is_production, true) = true
            GROUP BY date_plan::date
        )
        SELECT
            TO_CHAR(tanggal.date, 'DD') AS left_date,
            ROUND(COALESCE(a.tonnage, 0)::numeric, 2) AS total_tonnage,
            ROUND(COALESCE(p.plan_data, 0)::numeric, 2) AS total_plan
        FROM tanggal
        LEFT JOIN actual a
            ON tanggal.date = a.date
        LEFT JOIN plan p
            ON tanggal.date = p.date
        ORDER BY tanggal.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=["left_date", "total_tonnage", "total_plan"])

    df["total_tonnage"] = pd.to_numeric(df["total_tonnage"], errors="coerce").fillna(0.0).round(2)
    df["total_plan"] = pd.to_numeric(df["total_plan"], errors="coerce").fillna(0.0).round(2)

    return JsonResponse({
        "x_data": df["left_date"].tolist(),
        "total_tonnage": df["total_tonnage"].astype(float).tolist(),
        "total_plan": df["total_plan"].astype(float).tolist(),
    }, safe=False)

# http://kawi.localhost:8000/api/analytics/raw/mining/chart/?filter_type=weekly&filter_week=2025-04&iup_id=1
def get_weekly_chart(filter_week, iup_filter=None):
    iso_year, iso_week = map(int, filter_week.split("-"))

    start_date = date.fromisocalendar(iso_year, iso_week, 1)
    end_date = date.fromisocalendar(iso_year, iso_week, 7)

    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [start_date, end_date]
    plan_params = [start_date, end_date]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    params = [
        start_date,
        end_date,
        *actual_params,
        *plan_params,
    ]

    query = f"""
        WITH hari AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS tanggal
        ),
        actual AS (
            SELECT
                DATE(date_production) AS tanggal,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = true
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS ore,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = false
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS non_ore

            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY DATE(date_production)
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = true
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS ore_plan,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = false
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS non_ore_plan

            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY DATE(date_plan)
        )
        SELECT
            TO_CHAR(hari.tanggal, 'YYYY-MM-DD') AS tanggal,
            TO_CHAR(hari.tanggal, 'FMDy') AS hari,

            COALESCE(a.ore, 0)::numeric AS ore,
            COALESCE(p.ore_plan, 0)::numeric AS ore_plan,

            COALESCE(a.non_ore, 0)::numeric AS non_ore,
            COALESCE(p.non_ore_plan, 0)::numeric AS non_ore_plan

        FROM hari
        LEFT JOIN actual a
            ON hari.tanggal = a.tanggal
        LEFT JOIN plan p
            ON hari.tanggal = p.tanggal
        ORDER BY hari.tanggal
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "tanggal",
            "hari",
            "ore",
            "ore_plan",
            "non_ore",
            "non_ore_plan",
        ],
    )

    numeric_cols = [
        "ore",
        "ore_plan",
        "non_ore",
        "non_ore_plan",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["total_actual"] = df["ore"] + df["non_ore"]
    df["total_plan"] = df["ore_plan"] + df["non_ore_plan"]

    df["achievement"] = df.apply(
        lambda row: round((row["total_actual"] / row["total_plan"]) * 100, 2)
        if row["total_plan"] > 0
        else 0,
        axis=1,
    )

    df["achievement_ore"] = df.apply(
        lambda row: round((row["ore"] / row["ore_plan"]) * 100, 2)
        if row["ore_plan"] > 0
        else 0,
        axis=1,
    )

    df["achievement_non_ore"] = df.apply(
        lambda row: round((row["non_ore"] / row["non_ore_plan"]) * 100, 2)
        if row["non_ore_plan"] > 0
        else 0,
        axis=1,
    )

    return JsonResponse(
        {
            "x_data": df["hari"].astype(str).tolist(),

            "total_actual": df["total_actual"].round(1).astype(float).tolist(),
            "total_plan": df["total_plan"].round(1).astype(float).tolist(),
            "achievement": df["achievement"].round(1).astype(float).tolist(),

            "ore_actual": df["ore"].round(1).astype(float).tolist(),
            "ore_plan": df["ore_plan"].round(1).astype(float).tolist(),
            "ore_achievement": df["achievement_ore"].round(1).astype(float).tolist(),

            "non_ore_actual": df["non_ore"].round(1).astype(float).tolist(),
            "non_ore_plan": df["non_ore_plan"].round(1).astype(float).tolist(),
            "non_ore_achievement": df["achievement_non_ore"].round(1).astype(float).tolist(),
        },
        safe=False,
    )
# http://kawi.localhost:8000/api/analytics/raw/mining/chart/?filter_type=range&date_start='2026-03-01'&date_end='2026-03-20'&iup_id=1
def get_range_chart(date_start, date_end, iup_filter=None):
    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [date_start, date_end]
    plan_params = [date_start, date_end]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    params = [
        date_start,
        date_end,
        *actual_params,
        *plan_params,
    ]

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS tanggal
        ),

        actual AS (
            SELECT
                DATE(date_production) AS tanggal,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = true
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS ore,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = false
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS non_ore

            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY DATE(date_production)
        ),

        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = true
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS ore_plan,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = false
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS non_ore_plan

            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY DATE(date_plan)
        )

        SELECT
            TO_CHAR(tanggal.tanggal, 'YYYY-MM-DD') AS tanggal,

            COALESCE(a.ore, 0)::numeric AS ore,
            COALESCE(p.ore_plan, 0)::numeric AS ore_plan,

            COALESCE(a.non_ore, 0)::numeric AS non_ore,
            COALESCE(p.non_ore_plan, 0)::numeric AS non_ore_plan

        FROM tanggal
        LEFT JOIN actual a
            ON tanggal.tanggal = a.tanggal
        LEFT JOIN plan p
            ON tanggal.tanggal = p.tanggal
        ORDER BY tanggal.tanggal
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "tanggal",
            "ore",
            "ore_plan",
            "non_ore",
            "non_ore_plan",
        ],
    )

    numeric_cols = [
        "ore",
        "ore_plan",
        "non_ore",
        "non_ore_plan",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["total_actual"] = df["ore"] + df["non_ore"]
    df["total_plan"] = df["ore_plan"] + df["non_ore_plan"]

    df["achievement"] = df.apply(
        lambda row: round((row["total_actual"] / row["total_plan"]) * 100, 2)
        if row["total_plan"] > 0
        else 0,
        axis=1,
    )

    df["achievement_ore"] = df.apply(
        lambda row: round((row["ore"] / row["ore_plan"]) * 100, 2)
        if row["ore_plan"] > 0
        else 0,
        axis=1,
    )

    df["achievement_non_ore"] = df.apply(
        lambda row: round((row["non_ore"] / row["non_ore_plan"]) * 100, 2)
        if row["non_ore_plan"] > 0
        else 0,
        axis=1,
    )

    return JsonResponse(
        {
            "x_data": df["tanggal"].astype(str).tolist(),

            "total_actual": df["total_actual"].round(1).astype(float).tolist(),
            "total_plan": df["total_plan"].round(1).astype(float).tolist(),
            "achievement": df["achievement"].round(1).astype(float).tolist(),

            "ore_actual": df["ore"].round(1).astype(float).tolist(),
            "ore_plan": df["ore_plan"].round(1).astype(float).tolist(),
            "ore_achievement": df["achievement_ore"].round(1).astype(float).tolist(),

            "non_ore_actual": df["non_ore"].round(1).astype(float).tolist(),
            "non_ore_plan": df["non_ore_plan"].round(1).astype(float).tolist(),
            "non_ore_achievement": df["achievement_non_ore"].round(1).astype(float).tolist(),
        },
        safe=False,
    )

# http://kawi.localhost:8000/api/analytics/raw/mining/chart/?filter_type=yearly&filter_year=2025&iup_id=1
def get_yearly_chart(yearly, iup_filter=None):
    where_actual = "EXTRACT(YEAR FROM date_production) = %s"
    where_plan = "EXTRACT(YEAR FROM date_plan) = %s"

    actual_params = [yearly]
    plan_params = [yearly]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    params = [
        f"{yearly}-01-01",
        *actual_params,
        *plan_params,
    ]

    query = f"""
        WITH bulan AS (
            SELECT TO_CHAR(
                DATE_TRUNC('month', (DATE %s + (n || ' month')::interval)),
                'YYYY-MM'
            ) AS bulan
            FROM generate_series(0, 11) AS n
        ),

        actual AS (
            SELECT
                TO_CHAR(date_production, 'YYYY-MM') AS bulan,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = true
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS ore,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = false
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS non_ore

            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY TO_CHAR(date_production, 'YYYY-MM')
        ),

        plan AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY-MM') AS bulan,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = true
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS ore_plan,

                SUM(
                    CASE
                        WHEN COALESCE(is_ore, false) = false
                        AND COALESCE(is_production, true) = true
                        THEN tonnage ELSE 0
                    END
                )::numeric AS non_ore_plan

            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY TO_CHAR(date_plan, 'YYYY-MM')
        )

        SELECT
            b.bulan,

            COALESCE(a.ore, 0)::numeric AS ore,
            COALESCE(p.ore_plan, 0)::numeric AS ore_plan,

            COALESCE(a.non_ore, 0)::numeric AS non_ore,
            COALESCE(p.non_ore_plan, 0)::numeric AS non_ore_plan

        FROM bulan b
        LEFT JOIN actual a
            ON a.bulan = b.bulan
        LEFT JOIN plan p
            ON p.bulan = b.bulan
        ORDER BY b.bulan
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "bulan",
            "ore",
            "ore_plan",
            "non_ore",
            "non_ore_plan",
        ],
    )

    numeric_cols = ["ore", "ore_plan", "non_ore", "non_ore_plan"]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["total_actual"] = df["ore"] + df["non_ore"]
    df["total_plan"] = df["ore_plan"] + df["non_ore_plan"]

    df["achievement"] = df.apply(
        lambda row: round((row["total_actual"] / row["total_plan"] * 100), 2)
        if row["total_plan"] > 0
        else 0,
        axis=1,
    )

    df["achievement_ore"] = df.apply(
        lambda row: round((row["ore"] / row["ore_plan"] * 100), 2)
        if row["ore_plan"] > 0
        else 0,
        axis=1,
    )

    df["achievement_non_ore"] = df.apply(
        lambda row: round((row["non_ore"] / row["non_ore_plan"] * 100), 2)
        if row["non_ore_plan"] > 0
        else 0,
        axis=1,
    )

    x_data = df["bulan"].apply(
        lambda x: datetime.strptime(x, "%Y-%m").strftime("%b %y")
    ).tolist()

    return JsonResponse(
        {
            "x_data": x_data,

            "total_actual": df["total_actual"].round(1).astype(float).tolist(),
            "total_plan": df["total_plan"].round(1).astype(float).tolist(),
            "achievement": df["achievement"].round(1).astype(float).tolist(),

            "ore_actual": df["ore"].round(1).astype(float).tolist(),
            "ore_plan": df["ore_plan"].round(1).astype(float).tolist(),
            "ore_achievement": df["achievement_ore"].round(1).astype(float).tolist(),

            "non_ore_actual": df["non_ore"].round(1).astype(float).tolist(),
            "non_ore_plan": df["non_ore_plan"].round(1).astype(float).tolist(),
            "non_ore_achievement": df["achievement_non_ore"].round(1).astype(float).tolist(),
        },
        safe=False,
    )

def get_all_chart(iup_filter=None):
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH actual_per_year AS (
            SELECT
                TO_CHAR(date_production, 'YYYY') AS tahun,
                SUM(tonnage) AS total_tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            AND COALESCE(is_production, true) = true
            GROUP BY TO_CHAR(date_production, 'YYYY')
        ),

        plan_per_year AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY') AS tahun,
                SUM(tonnage) AS plan_data
            FROM view_mining_plan_productions
            WHERE {where_plan}
            AND COALESCE(is_production, true) = true
            GROUP BY TO_CHAR(date_plan, 'YYYY')
        )

        SELECT
            COALESCE(a.tahun, p.tahun) AS tahun,
            COALESCE(a.total_tonnage, 0) AS total_tonnage,
            COALESCE(p.plan_data, 0) AS plan_data
        FROM actual_per_year a
        FULL OUTER JOIN plan_per_year p
            ON a.tahun = p.tahun
        ORDER BY tahun
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=["tahun", "total_tonnage", "plan_data"])

    df["total"] = pd.to_numeric(df["total_tonnage"], errors="coerce").fillna(0.0).round(2)
    df["plan_data"] = pd.to_numeric(df["plan_data"], errors="coerce").fillna(0.0).round(2)

    df["achievement"] = df.apply(
        lambda row: round(float(row["total"]) / float(row["plan_data"]) * 100, 2)
        if float(row["plan_data"]) > 0
        else 0,
        axis=1,
    )

    return JsonResponse({
        "x_data": df["tahun"].tolist(),
        "total_actual": df["total"].tolist(),
        "total_plan": df["plan_data"].tolist(),
        "achievement": df["achievement"].tolist(),
    }, safe=False)