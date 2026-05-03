
# /services.py
from django.db import connection
from analytics.services import iup_filter
from analytics.services.iup_filter import build_iup_clause

def g(row, key):
    return row.get(key, 0) or 0

def fetch_production_mining(ds: str, de: str, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")

    query = f"""
        WITH day_series AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS dt
        ),
        prod AS (
            SELECT 
                DATE(mp.date_production) AS prod_date,
                SUM(CASE WHEN mp.nama_material = 'LIM' THEN mp.tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN mp.nama_material = 'SAP' THEN mp.tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN mp.nama_material = 'Waste' THEN mp.tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN mp.nama_material = 'Quarry' THEN mp.tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN mp.nama_material = 'Top Soil' THEN mp.tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN mp.nama_material = 'OB' THEN mp.tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN mp.nama_material = 'Ballast' THEN mp.tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN mp.nama_material = 'Biomass' THEN mp.tonnage ELSE 0 END)::numeric AS biomass,
                SUM(mp.tonnage)::numeric AS total
            FROM view_mining_productions mp
            WHERE mp.date_production BETWEEN %s AND %s
              {mp_iup_clause}
            GROUP BY DATE(mp.date_production)
        ),
        plan AS (
            SELECT
                DATE(pp.date_plan) AS plan_date,
                SUM(
                    COALESCE(pp.lim, 0) + COALESCE(pp.sap, 0) + COALESCE(pp.quarry, 0) +
                    COALESCE(pp.topsoil, 0) + COALESCE(pp.ob, 0) + COALESCE(pp.ballast, 0) +
                    COALESCE(pp.biomass, 0) + COALESCE(pp.waste, 0)
                )::numeric AS plan_total
            FROM mining_plan_productions pp
            WHERE pp.date_plan BETWEEN %s AND %s
                {pp_iup_clause}    
            GROUP BY DATE(pp.date_plan)
        )
        SELECT 
            ds.dt,
            COALESCE(mp.lim, 0) AS lim,
            COALESCE(mp.sap, 0) AS sap,
            COALESCE(mp.waste, 0) AS waste,
            COALESCE(mp.quarry, 0) AS quarry,
            COALESCE(mp.topsoil, 0) AS topsoil,
            COALESCE(mp.ob, 0) AS ob,
            COALESCE(mp.ballast, 0) AS ballast,
            COALESCE(mp.biomass, 0) AS biomass,
            COALESCE(mp.total, 0) AS actual_total,
            COALESCE(pp.plan_total, 0) AS plan_total
        FROM day_series ds
        LEFT JOIN prod mp ON ds.dt = mp.prod_date
        LEFT JOIN plan pp ON ds.dt = pp.plan_date
        ORDER BY ds.dt
    """
    params = [ds, de, ds, de] + mp_iup_params + [ds, de] + pp_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "total": sum(r["actual_total"] or 0 for r in rows),
        "plan": sum(r["plan_total"] or 0 for r in rows),
        "lim": sum(r["lim"] or 0 for r in rows),
        "sap": sum(r["sap"] or 0 for r in rows),
        "waste": sum(r["waste"] or 0 for r in rows),
        "quarry": sum(r["quarry"] or 0 for r in rows),
        "topsoil": sum(r["topsoil"] or 0 for r in rows),
        "ob": sum(r["ob"] or 0 for r in rows),
        "ballast": sum(r["ballast"] or 0 for r in rows),
        "biomass": sum(r["biomass"] or 0 for r in rows),
    }

    return {"rows": rows, "summary": summary}