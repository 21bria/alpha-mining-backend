
# /services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def g(row, key):
    return row.get(key, 0) or 0

def fetch_selling(ds: str, de: str, iup_filter=None):
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")

    query = f"""
        WITH day_series AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS dt
        ),
        actual AS (
            SELECT
                s.date_barge_out::date AS dt,
                SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END) AS lim,
                SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END) AS sap,
                SUM(s.tonnage) AS total
            FROM selling_barging s
            WHERE s.date_barge_out BETWEEN %s AND %s
              AND s.status_barging = 'Complete'
              {s_iup_clause}
            GROUP BY s.date_barge_out::date
        )
        SELECT
            ds.dt,
            COALESCE(a.lim, 0) AS actual_lim,
            COALESCE(a.sap, 0) AS actual_sap,
            COALESCE(a.total, 0) AS actual_total
        FROM day_series ds
        LEFT JOIN actual a ON ds.dt = a.dt
        ORDER BY ds.dt
    """

    params = [ds, de, ds, de] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "actual_total": sum(r["actual_total"] or 0 for r in rows),
        "lim_actual": sum(r["actual_lim"] or 0 for r in rows),
        "sap_actual": sum(r["actual_sap"] or 0 for r in rows),
    }

    return {"rows": rows, "summary": summary}

def fetch_barging(ds: str, de: str, iup_filter=None):
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
        ),
        detail AS (
            SELECT
                s.date_hauling::date AS date,
                mb.barge_code,
                ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
            FROM selling_barging s
            LEFT JOIN master_barge mb ON mb.id = s.barge_code
            LEFT JOIN master_materials m ON m.id = s.id_material
            WHERE s.date_hauling BETWEEN %s AND %s
              {s_iup_clause}
              -- AND s.status_barging = 'Complete'
            GROUP BY s.date_hauling::date, mb.barge_code
        )
        SELECT
            TO_CHAR(t.date, 'YY-MM-DD') AS label,
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
        FROM tanggal t
        LEFT JOIN detail d ON t.date = d.date
        GROUP BY t.date
        ORDER BY t.date
    """

    params = [ds, de, ds, de] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "actual_total": sum(r["actual_total"] or 0 for r in rows),
        "lim_actual": sum(r["actual_lim"] or 0 for r in rows),
        "sap_actual": sum(r["actual_sap"] or 0 for r in rows),
    }
    return {"rows": rows, "summary": summary}