
# reports/services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_barging_year(year: int, iup_filter=None):
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")
    p_iup_clause, p_iup_params = build_iup_clause(iup_filter, "p")

    query = f"""
        WITH bulan AS (
            SELECT 
                TO_CHAR(gs::date, 'YYYY-MM') AS bulan_key,
                TO_CHAR(gs::date, 'FMMonth') AS bulan_label
            FROM generate_series(
                make_date(%s, 1, 1),
                make_date(%s, 12, 31),
                interval '1 month'
            ) gs
        ),
        detail AS (
            SELECT
                TO_CHAR(s.date_hauling, 'YYYY-MM') AS bulan_key,
                mb.barge_code,
                ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
            FROM selling_barging s
            LEFT JOIN master_barge mb ON mb.id = s.barge_code
            LEFT JOIN master_materials m ON m.id = s.id_material
            WHERE EXTRACT(YEAR FROM s.date_hauling) = %s
            AND s.status_barging = 'Complete'
            {s_iup_clause}
            GROUP BY TO_CHAR(s.date_hauling, 'YYYY-MM'), mb.barge_code
        )
        SELECT
            b.bulan_key AS label,
            b.bulan_label,
            ROUND(COALESCE(SUM(d.total), 0), 2) AS actual_total,
            ROUND(COALESCE(SUM(d.lim), 0), 2) AS actual_lim,
            ROUND(COALESCE(SUM(d.sap), 0), 2) AS actual_sap,
            COALESCE(
                json_agg(
                    json_build_object(
                        'barge_code', d.barge_code,
                        'total', ROUND(d.total, 2),
                        'lim', ROUND(d.lim, 2),
                        'sap', ROUND(d.sap, 2)
                    )
                    ORDER BY d.barge_code
                ) FILTER (WHERE d.barge_code IS NOT NULL),
                '[]'::json
            ) AS summary_by_barge
        FROM bulan b
        LEFT JOIN detail d ON b.bulan_key = d.bulan_key
        GROUP BY b.bulan_key, b.bulan_label
        ORDER BY b.bulan_key
    """

    params = [year, year, year] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "actual_total": sum(r["actual_total"] or 0 for r in rows),
        "lim_actual": sum(r["actual_lim"] or 0 for r in rows),
        "sap_actual": sum(r["actual_sap"] or 0 for r in rows),
    }
    return {"rows": rows, "summary": summary}


def fetch_selling_year(year: int, iup_filter=None):
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")
    p_iup_clause, p_iup_params = build_iup_clause(iup_filter, "p")

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
        actual AS (
            SELECT
                TO_CHAR(s.date_barge_out, 'YYYY-MM') AS dt,
                SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric AS sap,
                SUM(s.tonnage)::numeric AS total
            FROM selling_barging s
            WHERE EXTRACT(YEAR FROM s.date_barge_out) = %s
              AND s.status_barging = 'Complete'
              {s_iup_clause}
            GROUP BY TO_CHAR(s.date_barge_out, 'YYYY-MM')
        )
        SELECT 
            b.dt,
            b.bulan_label,
            COALESCE(a.lim, 0)   AS actual_lim,
            COALESCE(a.sap, 0)   AS actual_sap,
            COALESCE(a.total, 0) AS actual_total
        FROM bulan b
        LEFT JOIN actual a ON b.dt = a.dt
        ORDER BY b.dt
    """

    params = [year, year, year] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "actual_total": sum(r["actual_total"] or 0 for r in rows),
        "lim_actual": sum(r["actual_lim"] or 0 for r in rows),
        "sap_actual": sum(r["actual_sap"] or 0 for r in rows),
    }
    return {"rows": rows, "summary": summary}
