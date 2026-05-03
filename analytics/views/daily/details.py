# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause

def get_daily_detail_productions(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")

    handlers = {
        "ore": get_daily_detail_ore,
        "ob": get_daily_detail_ob,
        "waste": get_daily_detail_waste,
        "quarry": get_daily_detail_quarry,
        "top_soil": get_daily_detail_top_soil,
        "others": get_daily_detail_others,
    }

    data = {
        key: func(filter_date, iup_filter)
        for key, func in handlers.items()
    }

    return JsonResponse(data, safe=True)

def get_daily_detail_ore(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")

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
                SUM(CASE WHEN mp.nama_material = 'LIM' THEN mp.tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN mp.nama_material = 'SAP' THEN mp.tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions mp
            WHERE mp.date_production = %s::date
            {mp_iup_clause}
            GROUP BY LPAD(t_load::text, 2, '0')
        ),
        plan_per_hour AS (
            SELECT
                SUM(COALESCE(pp.lim, 0) + COALESCE(pp.sap, 0))::numeric / 22 AS plan_data
            FROM mining_plan_productions pp
            WHERE pp.date_plan = %s::date
            {pp_iup_clause}
        )
        SELECT
            hs.hour_label AS id,
            hs.left_time,
            COALESCE(agg.lim, 0) AS lim,
            COALESCE(agg.sap, 0) AS sap,
            COALESCE(agg.lim, 0) + COALESCE(agg.sap, 0) AS total,
            COALESCE(p.plan_data, 0) AS plan_data
        FROM hour_series hs
        LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
        CROSS JOIN plan_per_hour p
        ORDER BY hs.sort_order;
    """

    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=["id", "left_time", "lim", "sap", "total", "plan_data"])

    for col in ["lim", "sap", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["achievement"] = df.apply(
        lambda r: round((r["total"] / r["plan_data"] * 100), 2) if r["plan_data"] > 0 else 0.0,
        axis=1
    )

    grand_total = {
        "lim": round(df["lim"].sum(), 2),
        "sap": round(df["sap"].sum(), 2),
        "total": round(df["total"].sum(), 2),
        "plan": round(df["plan_data"].sum(), 2),
        "achievement": round((df["total"].sum() / df["plan_data"].sum() * 100), 2) if df["plan_data"].sum() > 0 else 0.0,
        "avg": round(df["total"].mean(), 2),
    }

    return {
        "x_data": df["left_time"].tolist(),
        "lim_actual": df["lim"].tolist(),
        "sap_actual": df["sap"].tolist(),
        "total_actual": df["total"].tolist(),
        "total_plan": df["plan_data"].tolist(),
        "achievement": df["achievement"].tolist(),
        "grand_total": grand_total,
    }

def get_daily_detail_ob(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")
    
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
                    SUM(CASE WHEN nama_material IN ('OB') THEN tonnage ELSE 0 END)::numeric AS total_tonnage
                FROM view_mining_productions mp
                WHERE mp.date_production = %s::date
                {mp_iup_clause}
                GROUP BY LPAD(t_load::text, 2, '0')
            ),
            plan_per_hour AS (
                SELECT
                    ROUND(SUM(COALESCE(pp.ob,0))::numeric / 22, 3) AS plan_data
                FROM mining_plan_productions pp
                WHERE date_plan = %s::date
                {pp_iup_clause}
            )
            SELECT
                hs.hour_label AS id,
                hs.left_time,
                COALESCE(agg.total_tonnage, 0) AS total,
                p.plan_data
            FROM hour_series hs
            LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
            CROSS JOIN plan_per_hour p
            ORDER BY hs.sort_order;
    """

    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'left_time', 'total', 'plan_data'])
    df['total']         = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data']     = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0)
    df['achievement']   = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    # === Grand Total per tanggal ===
    grand_total = {
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement': round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }


    return {
        'x_data'       : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
        'total_actual' : df['total'].tolist(),
        'total_plan'   : df['plan_data'].tolist(),
        'achievement'  : df['achievement'].tolist(),
        'grand_total'  : grand_total
    }

def get_daily_detail_quarry(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")

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
                        SUM(CASE WHEN nama_material IN ('Quarry') THEN tonnage ELSE 0 END)::numeric AS total_tonnage
                    FROM view_mining_productions mp
                    WHERE mp.date_production = %s::date
                    {mp_iup_clause}
                    GROUP BY LPAD(t_load::text, 2, '0')
                ),
                plan_per_hour AS (
                    SELECT
                        ROUND(SUM(COALESCE(pp.quarry,0))::numeric / 22, 3) AS plan_data
                    FROM mining_plan_productions pp
                    WHERE date_plan = %s::date
                    {pp_iup_clause}
                )
                SELECT
                    hs.hour_label AS id,
                    hs.left_time,
                    COALESCE(agg.total_tonnage, 0) AS total,
                    p.plan_data
                FROM hour_series hs
                LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
                CROSS JOIN plan_per_hour p
                ORDER BY hs.sort_order;
    """
    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'left_time', 'total', 'plan_data'])
    df['total']       = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data']   = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    # === Grand Total per tanggal ===
    grand_total = {
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement': round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }


    return {
        'x_data'        : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
        'total_actual'  : df['total'].tolist(),
        'total_plan'    : df['plan_data'].tolist(),
        'achievement'   : df['achievement'].tolist(),
        'grand_total'   : grand_total
    }

def get_daily_detail_top_soil(filter_date, iup_filter=None):
    
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")

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
                    SUM(CASE WHEN nama_material IN ('Top Soil') THEN tonnage ELSE 0 END)::numeric AS total_tonnage
                FROM view_mining_productions mp
                WHERE mp.date_production = %s::date 
                {mp_iup_clause}
                GROUP BY LPAD(t_load::text, 2, '0')
            ),
            plan_per_hour AS (
                SELECT
                    ROUND(SUM(COALESCE(pp.topsoil,0))::numeric / 22, 3) AS plan_data
                FROM mining_plan_productions pp
                WHERE date_plan = %s::date
                {pp_iup_clause}
            )
            SELECT
                hs.hour_label AS id,
                hs.left_time,
                COALESCE(agg.total_tonnage, 0) AS total,
                p.plan_data
            FROM hour_series hs
            LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
            CROSS JOIN plan_per_hour p
            ORDER BY hs.sort_order;
    """

    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'left_time', 'total', 'plan_data'])
    df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    # === Grand Total per tanggal ===
    grand_total = {
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement' : round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }

    return {
        'x_data'        : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
        'total_actual'  : df['total'].tolist(),
        'total_plan'    : df['plan_data'].tolist(),
        'achievement'   : df['achievement'].tolist(),
        'grand_total'   : grand_total,
    }

def get_daily_detail_waste(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")   
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
                    SUM(CASE WHEN nama_material IN ('Waste') THEN tonnage ELSE 0 END)::numeric AS total_tonnage
                FROM view_mining_productions mp
                WHERE mp.date_production = %s::date
                {mp_iup_clause}
                GROUP BY LPAD(t_load::text, 2, '0')
            ),
            plan_per_hour AS (
                SELECT
                    ROUND(SUM(COALESCE(pp.waste,0))::numeric / 22, 3) AS plan_data
                FROM mining_plan_productions pp
                WHERE date_plan = %s::date
                {pp_iup_clause}
            )
            SELECT
                hs.hour_label AS id,
                hs.left_time,
                COALESCE(agg.total_tonnage, 0) AS total,
                p.plan_data
            FROM hour_series hs
            LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
            CROSS JOIN plan_per_hour p
            ORDER BY hs.sort_order;
    """

    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'left_time', 'total', 'plan_data'])
    df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    # === Grand Total per tanggal ===
    grand_total = {
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement': round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }

    return {
        'x_data'      : df['left_time'].tolist(),
        'total_actual': df['total'].tolist(),
        'total_plan'  : df['plan_data'].tolist(),
        'achievement' : df['achievement'].tolist(),
        'grand_total'  : grand_total,
    }

def get_daily_detail_others(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")
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
                    SUM(CASE WHEN nama_material IN ('Ballast','Biomass') THEN tonnage ELSE 0 END)::numeric AS total_tonnage
                FROM view_mining_productions mp
                WHERE mp.date_production = %s::date
                {mp_iup_clause}
                GROUP BY LPAD(t_load::text, 2, '0')
            ),
            plan_per_hour AS (
                SELECT
                    ROUND(SUM(COALESCE(pp.ballast,0) + COALESCE(pp.biomass,0))::numeric / 22, 3) AS plan_data
                FROM mining_plan_productions pp
                WHERE date_plan = %s::date
                {pp_iup_clause}
            )
            SELECT
                hs.hour_label AS id,
                hs.left_time,
                COALESCE(agg.total_tonnage, 0) AS total,
                p.plan_data
            FROM hour_series hs
            LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
            CROSS JOIN plan_per_hour p
            ORDER BY hs.sort_order;
    """

    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'left_time', 'total', 'plan_data'])
    df['total']         = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data']     = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0)
    df['achievement']   = df.apply(lambda r: round((r['total'] / r['plan_data'] * 100), 2) if r['plan_data'] > 0 else 0.0, axis=1)

    # === Grand Total per tanggal ===
    grand_total = {
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement' : round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }

    return {
        'x_data'        : df['left_time'].tolist(),
        'total_actual'  : df['total'].tolist(),
        'total_plan'    : df['plan_data'].tolist(),
        'achievement'   : df['achievement'].tolist(),
        'grand_total'   : grand_total
    }
