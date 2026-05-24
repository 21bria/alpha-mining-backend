import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import pandas as pd
from django.utils.timezone import now
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause

def parse_iso_week(week_value):
    iso_year_str, iso_week_str = str(week_value).split("-")
    return int(iso_year_str), int(iso_week_str)

def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

def build_filter_clause(period_start, period_end, iup_filter=None):
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

    group_actual = "DATE(a.date_production)"
    group_plan = "DATE(p.date_plan)"

    if period_start and period_end:
        where_actual += " AND DATE(a.date_production) BETWEEN %s AND %s"
        where_plan += " AND DATE(p.date_plan) BETWEEN %s AND %s"

        actual_params += [period_start, period_end]
        plan_params += [period_start, period_end]

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
        'lim', 'lim_plan', 'sap', 'sap_plan'
    ])

    return df

def generate_summary(df, label):
    ore_cols = ['lim', 'sap']
    lim_cols = ['lim']
    sap_cols = ['sap']
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']

    ore_plan_cols = [f'{f}_plan' for f in ore_cols]
    lim_plan_cols = [f'{f}_plan' for f in lim_cols]
    sap_plan_cols = [f'{f}_plan' for f in sap_cols]
    non_ore_plan_cols = [f'{f}_plan' for f in non_ore_cols]

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

    def material_summary(cols):
        return [
            {
                "material": col,
                "actual": float(round(df[col].sum(), 2)),
                "plan": float(round(df[f"{col}_plan"].sum(), 2)),
                "achievement": float(safe_div(df[col].sum(), df[f"{col}_plan"].sum()))
            }
            for col in cols
        ]

    return {
        'label': label,

        'ore_materials': material_summary(ore_cols),
        'non_ore_materials': material_summary(non_ore_cols),

        'total_ore': float(round(df['total_ore'].sum(), 2)),
        'total_ore_plan': float(round(df['total_ore_plan'].sum(), 2)),
        'achievement_ore': float(safe_div(df['total_ore'].sum(), df['total_ore_plan'].sum())),

        'total_non_ore': float(round(df['total_non_ore'].sum(), 2)),
        'total_non_ore_plan': float(round(df['total_non_ore_plan'].sum(), 2)),
        'achievement_non_ore': float(safe_div(df['total_non_ore'].sum(), df['total_non_ore_plan'].sum())),

        'total_actual': float(round(df['total_actual'].sum(), 2)),
        'total_plan': float(round(df['total_plan'].sum(), 2)),
        'achievement': float(safe_div(df['total_actual'].sum(), df['total_plan'].sum())),
        
    }

def get_summary_weekly(request):
    try:
        iup_filter = request.GET.get("iup_id")
        period_start = request.GET.get("period_start")
        period_end = request.GET.get("period_end")

        if not period_start or not period_end:
            return JsonResponse({
                "error": "period_start dan period_end wajib diisi"
            }, status=400)

        wa, wp, ga, gp, params = build_filter_clause(
            period_start,
            period_end,
            iup_filter
        )

        df = get_summary_dataframe(wa, wp, ga, gp, params)

        result = {
            "summary"       : generate_summary(df, "Weekly"),
            "period_start"  : period_start,
            "period_end"    : period_end,
        }

        return JsonResponse(result, safe=False)

    except DatabaseError as e:
        logger.error(f"Database query failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)