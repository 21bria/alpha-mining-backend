
# /services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def g(row, key):
    return row.get(key, 0) or 0

def fetch_production_quality(ds: str, de: str, iup_filter=None):
    op_iup_clause, op_iup_params = build_iup_clause(iup_filter, "op")

    query = f"""
        SELECT 
            op.tgl_production::date AS dt,
            SUM(op.tonnage) AS prod_total,
            SUM(CASE WHEN m.name = 'LIM' THEN op.tonnage ELSE 0 END) AS prod_lim,
            SUM(CASE WHEN m.name = 'SAP' THEN op.tonnage ELSE 0 END) AS prod_sap
        FROM geology_ore_productions op
        LEFT JOIN master_materials m ON m.id = op.id_material
        WHERE op.tgl_production BETWEEN %s AND %s
        {op_iup_clause}
        GROUP BY op.tgl_production::date
        ORDER BY op.tgl_production::date
    """

    params = [ds, de] + op_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "total": sum(r["prod_total"] or 0 for r in rows),
        "lim":   sum(r["prod_lim"] or 0 for r in rows),
        "sap":   sum(r["prod_sap"] or 0 for r in rows),
    }
    return {"rows": rows, "summary": summary}

def fetch_production_grade(ds: str, de: str, iup_filter=None):
    op_iup_clause, op_iup_params = build_iup_clause(iup_filter, "op")

    query = f"""
        WITH day_series AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS dt
        ),
        prod AS (
            SELECT
                DATE(op.tgl_production) AS prod_date,
                TRIM(op.nama_material) AS nama_material,
                SUM(op.tonnage)::numeric AS total_ore,
                SUM(
                    CASE 
                        WHEN op.roa_ni IS NOT NULL AND op.sample_number IS NOT NULL
                        THEN op.tonnage ELSE 0
                    END
                )::numeric AS released,
                SUM(op.tonnage * op.roa_ni) AS sum_ton_ni,
                SUM(op.tonnage * op.roa_co) AS sum_ton_co,
                SUM(op.tonnage * op.roa_fe) AS sum_ton_fe,
                SUM(op.tonnage * op.roa_mgo) AS sum_ton_mgo,
                SUM(op.tonnage * op.roa_sio2) AS sum_ton_sio2,
                SUM(
                    CASE 
                        WHEN op.sample_number IS NOT NULL AND op.roa_ni IS NOT NULL
                        THEN op.tonnage ELSE 0
                    END
                )::numeric AS denom_grade
            FROM view_geology_ore_details_roa op
            WHERE op.direct = 'No'
              AND op.tgl_production BETWEEN %s AND %s
              {op_iup_clause}
            GROUP BY DATE(op.tgl_production), TRIM(op.nama_material)
        )
        SELECT
            ds.dt,
            p.nama_material,
            COALESCE(p.total_ore, 0) AS total_ore,
            COALESCE(p.released, 0) AS released_ore,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_ni / p.denom_grade
                    ELSE 0
                END,
                'FM999999990.00'
            ) AS ni,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_co / p.denom_grade
                    ELSE 0
                END,
                'FM999999990.00'
            ) AS co,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_fe / p.denom_grade
                    ELSE 0
                END,
                'FM999999990.00'
            ) AS fe,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_mgo / p.denom_grade
                    ELSE 0
                END,
                'FM999999990.00'
            ) AS mgo,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0 THEN p.sum_ton_sio2 / p.denom_grade
                    ELSE 0
                END,
                'FM999999990.00'
            ) AS sio2,

            to_char(
                CASE 
                    WHEN p.denom_grade > 0
                     AND (p.sum_ton_mgo / p.denom_grade) > 0
                    THEN (p.sum_ton_sio2 / p.denom_grade) /
                         ((p.sum_ton_mgo / p.denom_grade) + 0.000001)
                    ELSE 0
                END,
                'FM999999990.00'
            ) AS sm
        FROM day_series ds
        LEFT JOIN prod p ON ds.dt = p.prod_date
        ORDER BY ds.dt, p.nama_material
    """

    params = [ds, de, ds, de] + op_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        grade_rows = [
            {
                "dt": r[0],
                "nama_material": r[1],
                "total_ore": float(r[2] or 0),
                "released_ore": float(r[3] or 0),
                "ni": r[4],
                "co": r[5],
                "fe": r[6],
                "mgo": r[7],
                "sio2": r[8],
                "sm": r[9],
            }
            for r in cur.fetchall()
        ]

    return {"rows": grade_rows}
