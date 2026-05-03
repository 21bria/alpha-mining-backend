from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_production_mining_year(year: int, iup_filter=None):
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    pp_iup_clause, pp_iup_params = build_iup_clause(iup_filter, "pp")

    query = f"""
        WITH bulan AS (
            SELECT 
                TO_CHAR(gs::date, 'YYYY-MM') AS dt,
                TO_CHAR(gs::date, 'FMMonth') AS bulan_label
            FROM generate_series(
                make_date(%s, 1, 1),
                make_date(%s, 12, 31),
                interval '1 month'
            ) gs
        ),
        prod AS (
            SELECT 
                TO_CHAR(mp.date_production, 'YYYY-MM') AS dt,
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
            WHERE EXTRACT(YEAR FROM mp.date_production) = %s
              {mp_iup_clause}
            GROUP BY TO_CHAR(mp.date_production, 'YYYY-MM')
        ),
        plan AS (
            SELECT
                TO_CHAR(pp.date_plan, 'YYYY-MM') AS dt,
                SUM(
                    COALESCE(pp.lim, 0) + COALESCE(pp.sap, 0) + COALESCE(pp.quarry, 0) + 
                    COALESCE(pp.topsoil, 0) + COALESCE(pp.ob, 0) + COALESCE(pp.ballast, 0) +
                    COALESCE(pp.biomass, 0) + COALESCE(pp.waste, 0)
                )::numeric AS plan_total
            FROM mining_plan_productions pp
            WHERE EXTRACT(YEAR FROM pp.date_plan) = %s
              {pp_iup_clause}
            GROUP BY TO_CHAR(pp.date_plan, 'YYYY-MM')
        )
        SELECT 
            b.dt,
            b.bulan_label,
            COALESCE(p.lim, 0) AS lim,
            COALESCE(p.sap, 0) AS sap,
            COALESCE(p.waste, 0) AS waste,
            COALESCE(p.quarry, 0) AS quarry,
            COALESCE(p.topsoil, 0) AS topsoil,
            COALESCE(p.ob, 0) AS ob,
            COALESCE(p.ballast, 0) AS ballast,
            COALESCE(p.biomass, 0) AS biomass,
            COALESCE(p.total, 0) AS actual_total,
            COALESCE(pl.plan_total, 0) AS plan_total
        FROM bulan b
        LEFT JOIN prod p ON b.dt = p.dt
        LEFT JOIN plan pl ON b.dt = pl.dt
        ORDER BY b.dt
    """

    params = [year, year, year] + mp_iup_params + [year] + pp_iup_params

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