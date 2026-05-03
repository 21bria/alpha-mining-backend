
# reports/services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_production_quality_year(year: int, iup_filter=None):
    op_iup_clause, op_iup_params = build_iup_clause(iup_filter, "op")

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
                TO_CHAR(op.tgl_production, 'YYYY-MM') AS dt,
                SUM(op.tonnage) AS prod_total,
                SUM(CASE WHEN m.name = 'LIM' THEN op.tonnage ELSE 0 END) AS prod_lim,
                SUM(CASE WHEN m.name = 'SAP' THEN op.tonnage ELSE 0 END) AS prod_sap
            FROM geology_ore_productions op
            LEFT JOIN master_materials m ON m.id = op.id_material
            WHERE EXTRACT(YEAR FROM op.tgl_production) = %s
              {op_iup_clause}
            GROUP BY TO_CHAR(op.tgl_production, 'YYYY-MM')
        )
        SELECT 
            b.dt,
            b.bulan_label,
            COALESCE(a.prod_total, 0) AS prod_total,
            COALESCE(a.prod_lim, 0) AS prod_lim,
            COALESCE(a.prod_sap, 0) AS prod_sap
        FROM bulan b
        LEFT JOIN actual a ON b.dt = a.dt
        ORDER BY b.dt
    """

    params = [year, year, year] + op_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "total": sum(r["prod_total"] or 0 for r in rows),
        "lim": sum(r["prod_lim"] or 0 for r in rows),
        "sap": sum(r["prod_sap"] or 0 for r in rows),
    }
    return {"rows": rows, "summary": summary}

def fetch_production_grade_year(year: int, iup_filter=None):
    p_iup_clause, p_iup_params = build_iup_clause(iup_filter, "p")

    query = f"""
        WITH month_series AS (
            SELECT 
                date_trunc('month', gs)::date AS dt,
                TO_CHAR(gs, 'YYYY-MM') AS dt_key,
                TO_CHAR(gs, 'FMMonth') AS dt_label
            FROM generate_series(
                make_date(%s, 1, 1),
                make_date(%s, 12, 31),
                interval '1 month'
            ) gs
        ),
        prod AS (
            SELECT
                date_trunc('month', p.tgl_production)::date AS prod_month,
                TRIM(p.nama_material) AS nama_material,
                SUM(p.tonnage)::numeric AS total_ore,
                SUM(
                    CASE 
                        WHEN p.roa_ni IS NOT NULL AND p.sample_number IS NOT NULL
                        THEN p.tonnage ELSE 0
                    END
                )::numeric AS released,
                SUM(p.tonnage * p.roa_ni) AS sum_ton_ni,
                SUM(p.tonnage * p.roa_co) AS sum_ton_co,
                SUM(p.tonnage * p.roa_fe) AS sum_ton_fe,
                SUM(p.tonnage * p.roa_mgo) AS sum_ton_mgo,
                SUM(p.tonnage * p.roa_sio2) AS sum_ton_sio2,
                SUM(
                    CASE 
                        WHEN p.sample_number IS NOT NULL AND p.roa_ni IS NOT NULL
                        THEN p.tonnage ELSE 0
                    END
                )::numeric AS denom_grade
            FROM view_geology_ore_details_roa p
            WHERE p.direct = 'No'
              AND EXTRACT(YEAR FROM p.tgl_production) = %s
              {p_iup_clause}
            GROUP BY 1, 2
        )
        SELECT
            ms.dt,
            ms.dt_key,
            TO_CHAR(ms.dt, 'Mon') AS bulan_label,
            p.nama_material,
            COALESCE(p.total_ore, 0) AS total_ore,
            COALESCE(p.released, 0) AS released_ore,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_ni / p.denom_grade
                    ELSE 0
                END,
                'FM999990.00'
            ) AS ni,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_co / p.denom_grade
                    ELSE 0
                END,
                'FM999990.00'
            ) AS co,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_fe / p.denom_grade
                    ELSE 0
                END,
                'FM999990.00'
            ) AS fe,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_mgo / p.denom_grade
                    ELSE 0
                END,
                'FM999990.00'
            ) AS mgo,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_sio2 / p.denom_grade
                    ELSE 0
                END,
                'FM999990.00'
            ) AS sio2,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0
                     AND (p.sum_ton_mgo / p.denom_grade) > 0
                    THEN (p.sum_ton_sio2 / p.denom_grade) /
                         ((p.sum_ton_mgo / p.denom_grade) + 0.000001)
                    ELSE 0
                END,
                'FM999990.00'
            ) AS sm
        FROM month_series ms
        LEFT JOIN prod p ON ms.dt = p.prod_month
        ORDER BY ms.dt, p.nama_material
    """

    params = [year, year, year] + p_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        grade_rows = [
            {
                "dt": r[0],              # date month start
                "dt_key": r[1],          # YYYY-MM
                "bulan_label": r[2],     # Jan, Feb, dst
                "nama_material": r[3],
                "total_ore": float(r[4] or 0),
                "released_ore": float(r[5] or 0),
                "ni": r[6],
                "co": r[7],
                "fe": r[8],
                "mgo": r[9],
                "sio2": r[10],
                "sm": r[11],
            }
            for r in cur.fetchall()
        ]

    summary = {
        "total": sum(r["total_ore"] for r in grade_rows),
        "lim": sum(r["total_ore"] for r in grade_rows if r["nama_material"] == "LIM"),
        "sap": sum(r["total_ore"] for r in grade_rows if r["nama_material"] == "SAP"),
    }

    return {"rows": grade_rows, "summary": summary}