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


def build_filter_clause(date_val, iup_filter=None):
    where_actual = "1=1"
    where_plan = "1=1"
    params = []

    group_actual = "DATE(mp.date_production)"
    group_plan = "DATE(pp.date_plan)"

    where_actual += " AND DATE(mp.date_production) = %s"
    where_plan += " AND DATE(pp.date_plan) = %s"
    params += [date_val, date_val]

    actual_iup_clause, actual_iup_params = build_iup_clause(iup_filter, "mp")
    plan_iup_clause, plan_iup_params = build_iup_clause(iup_filter, "pp")

    where_actual += actual_iup_clause
    where_plan += plan_iup_clause

    params += actual_iup_params + plan_iup_params

    return where_actual, where_plan, group_actual, group_plan, params

# For Summary plan vc actual
def get_summary_dataframe(where_actual, where_plan, group_actual, group_plan, params):
    query = f"""
        WITH actual AS (
            SELECT
                {group_actual} AS periode,
                SUM(CASE WHEN mp.nama_material = 'Top Soil' THEN mp.tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN mp.nama_material = 'OB' THEN mp.tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN mp.nama_material = 'Waste' THEN mp.tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN mp.nama_material = 'Quarry' THEN mp.tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN mp.nama_material = 'Ballast' THEN mp.tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN mp.nama_material = 'Biomass' THEN mp.tonnage ELSE 0 END)::numeric AS biomass,
                SUM(CASE WHEN mp.nama_material = 'LGLO' THEN mp.tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN mp.nama_material = 'MGLO' THEN mp.tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN mp.nama_material = 'HGLO' THEN mp.tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN mp.nama_material = 'MWS' THEN mp.tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN mp.nama_material = 'LGSO' THEN mp.tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN mp.nama_material = 'MGSO' THEN mp.tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN mp.nama_material = 'HGSO' THEN mp.tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN mp.nama_material = 'LIM' THEN mp.tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN mp.nama_material = 'SAP' THEN mp.tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions mp
            WHERE {where_actual}
            GROUP BY {group_actual}
        ),
        plan AS (
            SELECT
                {group_plan} AS periode,
                SUM(pp.topsoil)::numeric AS topsoil_plan,
                SUM(pp.ob)::numeric AS ob_plan,
                SUM(pp.waste)::numeric AS waste_plan,
                SUM(pp.quarry)::numeric AS quarry_plan,
                SUM(pp.ballast)::numeric AS ballast_plan,
                SUM(pp.biomass)::numeric AS biomass_plan,
                SUM(pp.lglo)::numeric AS lglo_plan,
                SUM(pp.mglo)::numeric AS mglo_plan,
                SUM(pp.hglo)::numeric AS hglo_plan,
                SUM(pp.mws)::numeric AS mws_plan,
                SUM(pp.lgso)::numeric AS lgso_plan,
                SUM(pp.mgso)::numeric AS mgso_plan,
                SUM(pp.hgso)::numeric AS hgso_plan,
                SUM(pp.lim)::numeric AS lim_plan,
                SUM(pp.sap)::numeric AS sap_plan
            FROM mining_plan_productions pp
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
    ore_cols = ['lglo', 'mglo', 'hglo', 'lgso', 'mgso', 'hgso', 'mws','lim','sap']
    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso', 'mws','sap']
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

def get_summary_daily_mining(request):
    iup_filter   = request.GET.get("iup_id")
    filter_date  = request.GET.get('filter_date')

    result = {}

    # === Daily ===
    wa, wp, ga, gp, params = build_filter_clause(filter_date, iup_filter)
    df_daily = get_summary_dataframe(wa, wp, ga, gp, params)
    result['daily'] = generate_summary(df_daily, 'Daily')

    return JsonResponse(result, safe=False)

# For Chart
def get_chart_daily_mining(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    return get_daily_chart(filter_date, iup_filter)

def get_daily_chart(filter_date, iup_filter=None):
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
                LPAD(mp.t_load::text, 2, '0') AS t_load_time,
                SUM(mp.tonnage) AS total_tonnage
            FROM view_mining_productions mp
            WHERE mp.date_production = %s::date
            {mp_iup_clause}
            GROUP BY LPAD(mp.t_load::text, 2, '0')
        ),
        plan_per_hour AS (
            SELECT
                ROUND((
                    SUM(
                        COALESCE(pp.topsoil, 0) + COALESCE(pp.ob, 0) + COALESCE(pp.lglo, 0) + COALESCE(pp.mglo, 0) +
                        COALESCE(pp.hglo, 0) + COALESCE(pp.waste, 0) + COALESCE(pp.mws, 0) + COALESCE(pp.lgso, 0) +
                        COALESCE(pp.mgso, 0) + COALESCE(pp.hgso, 0) + COALESCE(pp.lim, 0) + COALESCE(pp.sap, 0) +  
                        COALESCE(pp.quarry, 0) + COALESCE(pp.ballast, 0) + COALESCE(pp.biomass, 0)
                    ) / 22
                )::numeric, 2) AS plan_data
            FROM mining_plan_productions pp
            WHERE pp.date_plan = %s::date
            {pp_iup_clause}
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

    params = [filter_date] + mp_iup_params + [filter_date] + pp_iup_params

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


def get_summary_materials(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    return summary_materials(filter_date, iup_filter)


def summary_materials(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")

    query = f""" 
        SELECT 
            mp.nama_material,
            SUM(COALESCE(mp.tonnage, 0)) AS total_tonnage
        FROM view_mining_productions mp
        WHERE mp.date_production = %s
        {mp_iup_clause}
        GROUP BY mp.nama_material
        ORDER BY mp.nama_material;
    """

    params = [filter_date] + mp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    labels = [row[0] for row in data]
    y_data = [round(float(row[1] or 0), 1) for row in data]

    return JsonResponse({
        "labels": labels,
        "y_data": y_data
    })

# for summary grouped by material
def get_summary_materials_grouped(request):
    iup_filter = request.GET.get("iup_id")
    filter_date = request.GET.get("filter_date")
    return summary_materials_grouped(filter_date, iup_filter)

def summary_materials_grouped(filter_date, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")

    query = f"""
        SELECT 
            mp.shift,
            mp.nama_material,
            SUM(COALESCE(mp.ritase, 0)) AS total_ritase,
            SUM(COALESCE(mp.tonnage, 0)) AS total_tonnage
        FROM view_mining_productions mp
        WHERE mp.date_production = %s::date
        {mp_iup_clause}
        GROUP BY mp.shift, mp.nama_material
        ORDER BY mp.shift, mp.nama_material;
    """

    params = [filter_date] + mp_iup_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    summary_by_shift = defaultdict(lambda: {
        "total_ritase": 0,
        "total_tonnage": 0,
        "percentage": 0
    })

    detail = defaultdict(list)

    for shift, material, ritase, tonnage in rows:
        ritase = ritase or 0
        tonnage = float(tonnage or 0)

        summary_by_shift[shift]["total_ritase"] += ritase
        summary_by_shift[shift]["total_tonnage"] += tonnage

        detail[shift].append({
            "material": material,
            "ritase": ritase,
            "tonnage": round(tonnage, 2)
        })

    grand_total_tonnage = sum(
        v["total_tonnage"] for v in summary_by_shift.values()
    )

    if grand_total_tonnage > 0:
        for shift in summary_by_shift:
            summary_by_shift[shift]["percentage"] = round(
                (summary_by_shift[shift]["total_tonnage"] / grand_total_tonnage) * 100,
                2
            )

    return JsonResponse({
        "summary_by_shift": dict(summary_by_shift),
        "grand_total_tonnage": round(grand_total_tonnage, 2),
        "detail": dict(detail)
    })


