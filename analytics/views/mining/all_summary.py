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
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass,
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions a
            WHERE {where_actual}
            GROUP BY {group_actual}
        ),
        plan AS (
            SELECT
                {group_plan} AS periode,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan
            FROM mining_plan_productions p
            WHERE {where_plan}
            GROUP BY {group_plan}
        )
        SELECT
            COALESCE(a.periode, p.periode) AS periode,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(COALESCE(a.ob, 0), 2) AS ob,
            ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
            ROUND(COALESCE(a.waste, 0), 2) AS waste,
            ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
            ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
            ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
            ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
            ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
            ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
            ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan
        FROM actual a
        FULL OUTER JOIN plan p ON a.periode = p.periode
        ORDER BY periode
    """

    with connection.cursor() as cursor:
        print("WHERE ACTUAL:", where_actual)
        print("WHERE PLAN:", where_plan)
        print("PARAMS:", params)
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=[
        'periode', 'topsoil', 'topsoil_plan',
        'ob', 'ob_plan', 'waste', 'waste_plan', 'quarry', 'quarry_plan',
        'ballast', 'ballast_plan', 'biomass', 'biomass_plan',
        'lglo', 'lglo_plan', 'mglo', 'mglo_plan', 'hglo', 'hglo_plan',
        'mws', 'mws_plan', 'lgso', 'lgso_plan', 'mgso', 'mgso_plan', 'hgso', 'hgso_plan',
        'lim', 'lim_plan', 'sap', 'sap_plan'
    ])

    return df

def generate_summary(df, label):
    ore_cols = ['lglo', 'mglo', 'hglo', 'lgso', 'mgso', 'hgso', 'mws', 'lim', 'sap']
    lim_cols = ['lglo', 'mglo', 'hglo', 'lim']
    sap_cols = ['lgso', 'mgso', 'hgso', 'mws', 'sap']
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']

    ore_plan_cols = [f + '_plan' for f in ore_cols]
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    df['total_ore'] = df[ore_cols].sum(axis=1)
    df['total_ore_plan'] = df[ore_plan_cols].sum(axis=1)
    df['total_limonite'] = df[lim_cols].sum(axis=1)
    df['total_limonite_plan'] = df[lim_plan_cols].sum(axis=1)
    df['total_saprolite'] = df[sap_cols].sum(axis=1)
    df['total_saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['total_non_ore'] = df[non_ore_cols].sum(axis=1)
    df['total_non_ore_plan'] = df[non_ore_plan_cols].sum(axis=1)

    df['total_actual'] = df['total_ore'] + df['total_non_ore']
    df['total_plan'] = df['total_ore_plan'] + df['total_non_ore_plan']

    def safe_div(a, b):
        return round((a / b * 100), 0) if b > 0 else 0

    return {
        'label': label,
        'total_ore': float(round(df['total_ore'].sum(), 2)),
        'total_ore_plan': float(round(df['total_ore_plan'].sum(), 2)),
        'total_limonite': float(round(df['total_limonite'].sum(), 2)),
        'total_limonite_plan': float(round(df['total_limonite_plan'].sum(), 2)),
        'total_saprolite': float(round(df['total_saprolite'].sum(), 2)),
        'total_saprolite_plan': float(round(df['total_saprolite_plan'].sum(), 2)),
        'total_non_ore': float(round(df['total_non_ore'].sum(), 2)),
        'total_non_ore_plan': float(round(df['total_non_ore_plan'].sum(), 2)),
        'total_actual': float(round(df['total_actual'].sum(), 2)),
        'total_plan': float(round(df['total_plan'].sum(), 2)),
        'achievement': float(safe_div(df['total_actual'].sum(), df['total_plan'].sum())),
        'achievement_ore': float(safe_div(df['total_ore'].sum(), df['total_ore_plan'].sum())),
        'achievement_limonite': float(safe_div(df['total_limonite'].sum(), df['total_limonite_plan'].sum())),
        'achievement_saprolite': float(safe_div(df['total_saprolite'].sum(), df['total_saprolite_plan'].sum())),
        'achievement_non_ore': float(safe_div(df['total_non_ore'].sum(), df['total_non_ore_plan'].sum())),
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
    where_plan = "date_plan = %s::date"

    actual_params = [filter_date]
    plan_params = [filter_date]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND mp.iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
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
                LPAD(t_load::text, 2, '0') AS t_load_time,
                SUM(tonnage) AS total_tonnage
            FROM view_mining_productions mp
            WHERE {where_actual}
            GROUP BY LPAD(t_load::text, 2, '0')
        ),
        plan_per_hour AS (
            SELECT
                ROUND((
                    SUM(
                        COALESCE(topsoil, 0) + COALESCE(ob, 0) + COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                        COALESCE(hglo, 0) + COALESCE(waste, 0) + COALESCE(mws, 0) + COALESCE(lgso, 0) +
                        COALESCE(mgso, 0) + COALESCE(hgso, 0) + COALESCE(lim, 0) + COALESCE(sap, 0) +
                        COALESCE(quarry, 0) + COALESCE(ballast, 0) + COALESCE(biomass, 0)
                    ) / 22
                )::numeric, 2) AS plan_data
            FROM mining_plan_productions
            WHERE {where_plan}
        )
        SELECT
            hs.hour_label AS id,
            hs.left_time,
            COALESCE(a.total_tonnage, 0)::numeric(10,2) AS total,
            COALESCE(p.plan_data, 0)::numeric(10,2) AS plan_data
        FROM hour_series hs
        LEFT JOIN agg_data a ON hs.left_time = a.t_load_time
        CROSS JOIN plan_per_hour p
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
        lambda r: round((r["total"] / r["plan_data"] * 100), 2) if r["plan_data"] > 0 else 0.0,
        axis=1
    )

    return JsonResponse({
        "x_data": df["left_time"].tolist(),
        "total_actual": df["total"].tolist(),
        "total_plan": df["plan_data"].tolist(),
        "achievement": df["achievement"].tolist(),
    }, safe=False)

def get_chart_ore_quality(request):
    iup_filter   = request.GET.get("iup_id")
    filter_type  = request.GET.get("filter_type")
    filter_date  = request.GET.get("filter_date")

    if filter_type == "daily" and filter_date:
        return get_daily_ore_chart(filter_date, iup_filter)

    return JsonResponse({"error": "Invalid filter"}, status=400)

def get_daily_ore_chart(filter_date, iup_filter=None):
    where_actual = "date_production = %s"
    where_plan = "date_plan = %s"

    actual_params = [filter_date]
    plan_params = [filter_date]

    # FILTER IUP
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
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

        -- ACTUAL (produksi)
        agg_actual AS (
            SELECT 
                TO_CHAR(make_time(t_load::int, 0, 0), 'HH24') AS t_load_time,
                 SUM(tonnage) AS total_tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY t_load
        ),

        --PLAN (dipisah, tidak join langsung)
        agg_plan AS (
            SELECT 
                ROUND((
                    SUM(
                        COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                        COALESCE(hglo, 0) + COALESCE(mws, 0) +
                        COALESCE(lgso, 0) + COALESCE(mgso, 0) +
                        COALESCE(hgso, 0) + COALESCE(lim, 0) +
                        COALESCE(sap, 0)
                    ) / 22
                )::numeric, 2) AS plan_data
            FROM mining_plan_productions
            WHERE {where_plan}
        )

        SELECT
            hs.hour_label AS id,
            hs.left_time,
            COALESCE(a.total_tonnage, 0)::numeric(10,2) AS total,
            COALESCE(p.plan_data, 0)::numeric(10,2) AS plan_data
        FROM hour_series hs
        LEFT JOIN agg_actual a ON hs.left_time = a.t_load_time
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
        if r["plan_data"] > 0 else 0.0,
        axis=1
    )

    return JsonResponse({
        "x_data": df["left_time"].tolist(),
        "total_actual": df["total"].tolist(),
        "total_plan": df["plan_data"].tolist(),
        "achievement": df["achievement"].tolist(),
    }, safe=False)

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

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    # params untuk generate_series + actual + plan
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
            GROUP BY date_production::date
        ),
        plan AS (
            SELECT 
                date_plan::date AS date,
                SUM(
                    COALESCE(topsoil, 0) + COALESCE(ob, 0) + COALESCE(lglo, 0) + 
                    COALESCE(mglo, 0) + COALESCE(hglo, 0) + COALESCE(waste, 0) + 
                    COALESCE(mws, 0) + COALESCE(lgso, 0) + COALESCE(mgso, 0) + 
                    COALESCE(hgso, 0) + COALESCE(lim, 0) + COALESCE(sap, 0) + 
                    COALESCE(quarry, 0) + COALESCE(ballast, 0) + COALESCE(biomass, 0)
                ) AS plan_data
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY date_plan::date
        )
        SELECT
            TO_CHAR(tanggal.date, 'DD') AS left_date,
            ROUND(COALESCE(a.tonnage, 0)::numeric, 2) AS total_tonnage,
            ROUND(COALESCE(p.plan_data, 0)::numeric, 2) AS total_plan
        FROM tanggal
        LEFT JOIN actual a ON tanggal.date = a.date
        LEFT JOIN plan p ON tanggal.date = p.date
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
    iso_year, iso_week = map(int, filter_week.split('-'))

    start_date = date.fromisocalendar(iso_year, iso_week, 1)
    end_date   = date.fromisocalendar(iso_year, iso_week, 7)

    where_actual = "TO_CHAR(date_production, 'IYYY-IW') = %s"
    where_plan   = "TO_CHAR(date_plan, 'IYYY-IW') = %s"

    actual_params = [filter_week]
    plan_params   = [filter_week]

    # FILTER IUP
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan   += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params   += iup_ids

    params = [
        start_date, end_date,
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
                TO_CHAR(date_production, 'FMDy') AS nama_hari,
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY DATE(date_production), TO_CHAR(date_production, 'FMDy')
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,
                TO_CHAR(date_plan, 'FMDy') AS nama_hari,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY DATE(date_plan), TO_CHAR(date_plan, 'FMDy')
        )
        SELECT
            TO_CHAR(hari.tanggal, 'YYYY-MM-DD') AS tanggal,
            TO_CHAR(hari.tanggal, 'FMDy') AS hari,

            COALESCE(a.lglo, 0) AS lglo,
            COALESCE(p.lglo_plan, 0) AS lglo_plan,

            COALESCE(a.mglo, 0) AS mglo,
            COALESCE(p.mglo_plan, 0) AS mglo_plan,

            COALESCE(a.hglo, 0) AS hglo,
            COALESCE(p.hglo_plan, 0) AS hglo_plan,

            COALESCE(a.mws, 0) AS mws,
            COALESCE(p.mws_plan, 0) AS mws_plan,

            COALESCE(a.lgso, 0) AS lgso,
            COALESCE(p.lgso_plan, 0) AS lgso_plan,

            COALESCE(a.mgso, 0) AS mgso,
            COALESCE(p.mgso_plan, 0) AS mgso_plan,

            COALESCE(a.hgso, 0) AS hgso,
            COALESCE(p.hgso_plan, 0) AS hgso_plan,

            COALESCE(a.lim, 0) AS lim,
            COALESCE(p.lim_plan, 0) AS lim_plan,

            COALESCE(a.sap, 0) AS sap,
            COALESCE(p.sap_plan, 0) AS sap_plan,

            COALESCE(a.topsoil, 0) AS topsoil,
            COALESCE(p.topsoil_plan, 0) AS topsoil_plan,

            COALESCE(a.ob, 0) AS ob,
            COALESCE(p.ob_plan, 0) AS ob_plan,

            COALESCE(a.waste, 0) AS waste,
            COALESCE(p.waste_plan, 0) AS waste_plan,

            COALESCE(a.quarry, 0) AS quarry,
            COALESCE(p.quarry_plan, 0) AS quarry_plan,

            COALESCE(a.ballast, 0) AS ballast,
            COALESCE(p.ballast_plan, 0) AS ballast_plan,

            COALESCE(a.biomass, 0) AS biomass,
            COALESCE(p.biomass_plan, 0) AS biomass_plan
        FROM hari
        LEFT JOIN actual a ON hari.tanggal = a.tanggal
        LEFT JOIN plan p ON hari.tanggal = p.tanggal
        ORDER BY hari.tanggal
    """

    # params = [filter_week, filter_week]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

        columns = [
            'tanggal', 'hari',
            'lglo', 'lglo_plan',
            'mglo', 'mglo_plan',
            'hglo', 'hglo_plan',
            'mws', 'mws_plan',
            'lgso', 'lgso_plan',
            'mgso', 'mgso_plan',
            'hgso', 'hgso_plan',
            'lim', 'lim_plan',
            'sap', 'sap_plan',
            'topsoil', 'topsoil_plan',
            'ob', 'ob_plan',
            'waste', 'waste_plan',
            'quarry', 'quarry_plan',
            'ballast', 'ballast_plan',
            'biomass', 'biomass_plan',
    ]

    df = pd.DataFrame(data, columns=columns)

    metric_cols = [
        'lglo', 'mglo', 'hglo', 'mws',
        'lgso', 'mgso', 'hgso',
        'lim', 'sap',
        'topsoil', 'ob', 'waste',
        'quarry', 'ballast', 'biomass'
    ]

    # pastikan numeric
    for col in metric_cols:
        plan_col = f"{col}_plan"
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df[plan_col] = pd.to_numeric(df[plan_col], errors='coerce').fillna(0)

    # hitung achievement per kolom
    for col in metric_cols:
        plan_col = f"{col}_plan"
        ach_col = f"{col}_ach"

        df[ach_col] = df.apply(
            lambda row: round((row[col] / row[plan_col]) * 100, 2) if row[plan_col] > 0 else 0,
            axis=1
        )

    # kategori total
    lim_cols = ['lglo', 'mglo', 'hglo', 'lim']
    sap_cols = ['lgso', 'mgso', 'hgso', 'mws', 'sap']
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']

    lim_plan_cols = [f"{c}_plan" for c in lim_cols]
    sap_plan_cols = [f"{c}_plan" for c in sap_cols]
    non_ore_plan_cols = [f"{c}_plan" for c in non_ore_cols]

    df['total_lim'] = df[lim_cols].sum(axis=1)
    df['total_lim_plan'] = df[lim_plan_cols].sum(axis=1)

    df['total_sap'] = df[sap_cols].sum(axis=1)
    df['total_sap_plan'] = df[sap_plan_cols].sum(axis=1)

    df['total_non_ore'] = df[non_ore_cols].sum(axis=1)
    df['total_non_ore_plan'] = df[non_ore_plan_cols].sum(axis=1)

    df['total_actual'] = df['total_lim'] + df['total_sap'] + df['total_non_ore']
    df['total_plan'] = df['total_lim_plan'] + df['total_sap_plan'] + df['total_non_ore_plan']

    df['total_achievement'] = df.apply(
        lambda row: round((row['total_actual'] / row['total_plan']) * 100, 2) if row['total_plan'] > 0 else 0,
        axis=1
    )

    df['limonite_ach']  = df.apply(lambda r: round((r['total_lim'] / r['total_lim_plan'] * 100), 2) if r['total_lim_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['total_sap'] / r['total_sap_plan'] * 100), 2) if r['total_sap_plan'] > 0 else 0, axis=1)

    df['non_ore_ach']   = df.apply(lambda r: round((r['total_non_ore'] / r['total_non_ore_plan'] * 100), 2) if r['total_non_ore_plan'] > 0 else 0, axis=1)


    return JsonResponse({
        'x_data'        : df['hari'].astype(str).tolist(),
        'total_actual' : df['total_actual'].round(1).tolist(),
        'total_plan'   : df['total_plan'].round(1).tolist(),
        'achievement'  : df['total_achievement'].round(1).tolist(),
    }, safe=False)

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
        date_start, date_end,
        *actual_params,
        *plan_params,
    ]

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
        ),
        actual AS (
            SELECT
                DATE(date_production) AS tanggal,
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY DATE(date_production)
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY DATE(date_plan)
        )
        SELECT
            TO_CHAR(tanggal.date, 'YYYY-MM-DD') AS tanggal,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(CASE WHEN p.lglo_plan > 0 THEN (a.lglo * 100.0 / p.lglo_plan)::numeric ELSE 0 END, 2) AS lglo_ach,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(CASE WHEN p.mglo_plan > 0 THEN (a.mglo * 100.0 / p.mglo_plan)::numeric ELSE 0 END, 2) AS mglo_ach,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(CASE WHEN p.hglo_plan > 0 THEN (a.hglo * 100.0 / p.hglo_plan)::numeric ELSE 0 END, 2) AS hglo_ach,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(CASE WHEN p.mws_plan > 0 THEN (a.mws * 100.0 / p.mws_plan)::numeric ELSE 0 END, 2) AS mws_ach,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(CASE WHEN p.lgso_plan > 0 THEN (a.lgso * 100.0 / p.lgso_plan)::numeric ELSE 0 END, 2) AS lgso_ach,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(CASE WHEN p.mgso_plan > 0 THEN (a.mgso * 100.0 / p.mgso_plan)::numeric ELSE 0 END, 2) AS mgso_ach,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(CASE WHEN p.hgso_plan > 0 THEN (a.hgso * 100.0 / p.hgso_plan)::numeric ELSE 0 END, 2) AS hgso_ach,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(CASE WHEN p.lim_plan > 0 THEN (a.lim * 100.0 / p.lim_plan)::numeric ELSE 0 END, 2) AS lim_ach,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan,
            ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach,
            ROUND(COALESCE(a.ob, 0), 2) AS ob,
            ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
            ROUND(CASE WHEN p.ob_plan > 0 THEN (a.ob * 100.0 / p.ob_plan)::numeric ELSE 0 END, 2) AS ob_ach,
            ROUND(COALESCE(a.waste, 0), 2) AS waste,
            ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
            ROUND(CASE WHEN p.waste_plan > 0 THEN (a.waste * 100.0 / p.waste_plan)::numeric ELSE 0 END, 2) AS waste_ach,
            ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
            ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
            ROUND(CASE WHEN p.quarry_plan > 0 THEN (a.quarry * 100.0 / p.quarry_plan)::numeric ELSE 0 END, 2) AS quarry_ach,
            ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
            ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
            ROUND(CASE WHEN p.ballast_plan > 0 THEN (a.ballast * 100.0 / p.ballast_plan)::numeric ELSE 0 END, 2) AS ballast_ach,
            ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
            ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
            ROUND(CASE WHEN p.biomass_plan > 0 THEN (a.biomass * 100.0 / p.biomass_plan)::numeric ELSE 0 END, 2) AS biomass_ach
        FROM tanggal
        LEFT JOIN actual a ON tanggal.date = a.tanggal
        LEFT JOIN plan p ON tanggal.date = p.tanggal
        ORDER BY tanggal.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = [
        'tanggal',
        'lglo', 'lglo_plan', 'lglo_ach',
        'mglo', 'mglo_plan', 'mglo_ach',
        'hglo', 'hglo_plan', 'hglo_ach',
        'mws',  'mws_plan',  'mws_ach',
        'lgso', 'lgso_plan', 'lgso_ach',
        'mgso', 'mgso_plan', 'mgso_ach',
        'hgso', 'hgso_plan', 'hgso_ach',
        'lim', 'lim_plan', 'lim_ach',
        'sap', 'sap_plan', 'sap_ach',
        'topsoil', 'topsoil_plan', 'topsoil_ach',
        'ob', 'ob_plan', 'ob_ach',
        'waste', 'waste_plan', 'waste_ach',
        'quarry', 'quarry_plan', 'quarry_ach',
        'ballast', 'ballast_plan', 'ballast_ach',
        'biomass', 'biomass_plan', 'biomass_ach',
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols + non_ore_cols + non_ore_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['non_ore']        = df[non_ore_cols].sum(axis=1)
    df['non_ore_plan']   = df[non_ore_plan_cols].sum(axis=1)
    

    df['total_actual'] = df['limonite'] + df['saprolite'] + df['non_ore'] 
    df['total_plan']   = df['limonite_plan'] + df['saprolite_plan'] +  df['non_ore_plan']
    df['achievement']  = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    df['non_ore_ach']   = df.apply(lambda r: round((r['non_ore'] / r['non_ore_plan'] * 100), 2) if r['non_ore_plan'] > 0 else 0, axis=1)


    return JsonResponse({
        'x_data'       : df['tanggal'].astype(str).tolist(),
        'total_actual' : df['total_actual'].round(1).tolist(),
        'total_plan'   : df['total_plan'].round(1).tolist(),
        'achievement'  : df['achievement'].round(1).tolist(),
    }, safe=False)

# http://kawi.localhost:8000/api/analytics/raw/mining/chart/?filter_type=yearly&filter_year=2025&iup_id=1
def get_yearly_chart(yearly, iup_filter=None):
    where_actual = "EXTRACT(YEAR FROM date_production) = %s"
    where_plan = "EXTRACT(YEAR FROM date_plan) = %s"

    actual_params = [yearly]
    plan_params = [yearly]

    # filter iup
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
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY TO_CHAR(date_production, 'YYYY-MM')
        ),
        plan AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY-MM') AS bulan,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY TO_CHAR(date_plan, 'YYYY-MM')
        )
        SELECT
            b.bulan,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(CASE WHEN COALESCE(p.lglo_plan, 0) > 0 THEN (COALESCE(a.lglo, 0) * 100.0 / p.lglo_plan)::numeric ELSE 0 END, 2) AS lglo_ach,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(CASE WHEN COALESCE(p.mglo_plan, 0) > 0 THEN (COALESCE(a.mglo, 0) * 100.0 / p.mglo_plan)::numeric ELSE 0 END, 2) AS mglo_ach,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(CASE WHEN COALESCE(p.hglo_plan, 0) > 0 THEN (COALESCE(a.hglo, 0) * 100.0 / p.hglo_plan)::numeric ELSE 0 END, 2) AS hglo_ach,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(CASE WHEN COALESCE(p.mws_plan, 0) > 0 THEN (COALESCE(a.mws, 0) * 100.0 / p.mws_plan)::numeric ELSE 0 END, 2) AS mws_ach,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(CASE WHEN COALESCE(p.lgso_plan, 0) > 0 THEN (COALESCE(a.lgso, 0) * 100.0 / p.lgso_plan)::numeric ELSE 0 END, 2) AS lgso_ach,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(CASE WHEN COALESCE(p.mgso_plan, 0) > 0 THEN (COALESCE(a.mgso, 0) * 100.0 / p.mgso_plan)::numeric ELSE 0 END, 2) AS mgso_ach,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(CASE WHEN COALESCE(p.hgso_plan, 0) > 0 THEN (COALESCE(a.hgso, 0) * 100.0 / p.hgso_plan)::numeric ELSE 0 END, 2) AS hgso_ach,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(CASE WHEN COALESCE(p.lim_plan, 0) > 0 THEN (COALESCE(a.lim, 0) * 100.0 / p.lim_plan)::numeric ELSE 0 END, 2) AS lim_ach,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan,
            ROUND(CASE WHEN COALESCE(p.sap_plan, 0) > 0 THEN (COALESCE(a.sap, 0) * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN COALESCE(p.topsoil_plan, 0) > 0 THEN (COALESCE(a.topsoil, 0) * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach,
            ROUND(COALESCE(a.ob, 0), 2) AS ob,
            ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
            ROUND(CASE WHEN COALESCE(p.ob_plan, 0) > 0 THEN (COALESCE(a.ob, 0) * 100.0 / p.ob_plan)::numeric ELSE 0 END, 2) AS ob_ach,
            ROUND(COALESCE(a.waste, 0), 2) AS waste,
            ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
            ROUND(CASE WHEN COALESCE(p.waste_plan, 0) > 0 THEN (COALESCE(a.waste, 0) * 100.0 / p.waste_plan)::numeric ELSE 0 END, 2) AS waste_ach,
            ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
            ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
            ROUND(CASE WHEN COALESCE(p.quarry_plan, 0) > 0 THEN (COALESCE(a.quarry, 0) * 100.0 / p.quarry_plan)::numeric ELSE 0 END, 2) AS quarry_ach,
            ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
            ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
            ROUND(CASE WHEN COALESCE(p.ballast_plan, 0) > 0 THEN (COALESCE(a.ballast, 0) * 100.0 / p.ballast_plan)::numeric ELSE 0 END, 2) AS ballast_ach,
            ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
            ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
            ROUND(CASE WHEN COALESCE(p.biomass_plan, 0) > 0 THEN (COALESCE(a.biomass, 0) * 100.0 / p.biomass_plan)::numeric ELSE 0 END, 2) AS biomass_ach
        FROM bulan b
        LEFT JOIN actual a ON a.bulan = b.bulan
        LEFT JOIN plan p ON p.bulan = b.bulan
        ORDER BY b.bulan
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = [
        'bulan',
        'lglo', 'lglo_plan', 'lglo_ach',
        'mglo', 'mglo_plan', 'mglo_ach',
        'hglo', 'hglo_plan', 'hglo_ach',
        'mws',  'mws_plan',  'mws_ach',
        'lgso', 'lgso_plan', 'lgso_ach',
        'mgso', 'mgso_plan', 'mgso_ach',
        'hgso', 'hgso_plan', 'hgso_ach',
        'lim', 'lim_plan', 'lim_ach',
        'sap', 'sap_plan', 'sap_ach',
        'topsoil', 'topsoil_plan', 'topsoil_ach',
        'ob', 'ob_plan', 'ob_ach',
        'waste', 'waste_plan', 'waste_ach',
        'quarry', 'quarry_plan', 'quarry_ach',
        'ballast', 'ballast_plan', 'ballast_ach',
        'biomass', 'biomass_plan', 'biomass_ach',
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols + non_ore_cols + non_ore_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['non_ore']        = df[non_ore_cols].sum(axis=1)
    df['non_ore_plan']   = df[non_ore_plan_cols].sum(axis=1)
    
    df['total_actual']  = df['limonite'] + df['saprolite'] + df['non_ore'] 
    df['total_plan']    = df['limonite_plan'] + df['saprolite_plan'] +  df['non_ore_plan']
    df['achievement']   = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    df['non_ore_ach']   = df.apply(lambda r: round((r['non_ore'] / r['non_ore_plan'] * 100), 2) if r['non_ore_plan'] > 0 else 0, axis=1)

    # Define month names
    x_data = df['bulan'].apply(lambda x: datetime.strptime(x, '%Y-%m').strftime('%b %y')).tolist()


    return JsonResponse({
        'x_data'       : x_data,
        'total_actual' : df['total_actual'].round(1).tolist(),
        'total_plan'   : df['total_plan'].round(1).tolist(),
        'achievement'  : df['achievement'].round(1).tolist(),
    }, safe=False)

def get_all_chart(iup_filter=None):
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    # filter iup
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
            GROUP BY TO_CHAR(date_production, 'YYYY')
        ),
        plan_per_year AS (
            SELECT 
                TO_CHAR(date_plan, 'YYYY') AS tahun,
                SUM(
                    COALESCE(topsoil, 0) + COALESCE(ob, 0) + COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                    COALESCE(hglo, 0) + COALESCE(waste, 0) + COALESCE(mws, 0) + COALESCE(lgso, 0) +
                    COALESCE(mgso, 0) + COALESCE(hgso, 0) + COALESCE(lim, 0) + COALESCE(sap, 0) + 
                    COALESCE(quarry, 0) + COALESCE(ballast, 0) + COALESCE(biomass, 0)
                ) AS plan_data
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY TO_CHAR(date_plan, 'YYYY')
        )
        SELECT 
            COALESCE(a.tahun, p.tahun) AS tahun,
            COALESCE(a.total_tonnage, 0) AS total_tonnage,
            COALESCE(p.plan_data, 0) AS plan_data
        FROM actual_per_year a
        FULL OUTER JOIN plan_per_year p ON a.tahun = p.tahun
        ORDER BY tahun
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['tahun','total_tonnage', 'plan_data'])
    df['total'] = pd.to_numeric(df['total_tonnage'], errors='coerce').fillna(0.0).round(2)
    df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0).round(2)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    return JsonResponse({
        'x_data'      : df['tahun'].tolist(), 
        'total_actual': df['total'].tolist(),
        'total_plan'  : df['plan_data'].tolist(),
        'achievement' : df['achievement'].tolist(),
    }, safe=False)
