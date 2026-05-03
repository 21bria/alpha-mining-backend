
# reports/services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_inventory_balance_year(year: int, iup_filter=None):
    g_iup_clause, g_iup_params = build_iup_clause(iup_filter, "g")
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")
    g2_iup_clause, g2_iup_params = build_iup_clause(iup_filter, "g2")
    s2_iup_clause, s2_iup_params = build_iup_clause(iup_filter, "s2")

    query = f"""
        WITH bulan AS (
            SELECT
                TO_CHAR(gs::date, 'YYYY-MM') AS dt,
                TO_CHAR(gs::date, 'FMMonth') AS bulan_label
            FROM generate_series(
                make_date(%s, 1, 1),
                make_date(%s, 12, 1),
                interval '1 month'
            ) gs
        ),
        incoming AS (
            SELECT
                TO_CHAR(g.tgl_production, 'YYYY-MM') AS dt,
                SUM(g.tonnage) AS total_in,
                SUM(
                    CASE
                        WHEN g.status_dome = 'Finished' THEN 0
                        ELSE g.tonnage
                    END
                ) AS in_stock
            FROM geology_ore_productions g
            WHERE EXTRACT(YEAR FROM g.tgl_production) = %s
              {g_iup_clause}
            GROUP BY TO_CHAR(g.tgl_production, 'YYYY-MM')
        ),
        outgoing AS (
            SELECT
                TO_CHAR(s.date_hauling, 'YYYY-MM') AS dt,
                SUM(s.tonnage) AS total_out,
                SUM(
                    CASE
                        WHEN s.sale_dome = 'Finished' THEN 0
                        ELSE s.tonnage
                    END
                ) AS out_stock
            FROM selling_barging s
            WHERE EXTRACT(YEAR FROM s.date_hauling) = %s
              AND s.status_barging = 'Complete'
              {s_iup_clause}
            GROUP BY TO_CHAR(s.date_hauling, 'YYYY-MM')
        ),
        saldo_awal AS (
            SELECT
                COALESCE((
                    SELECT SUM(
                        CASE
                            WHEN g2.status_dome = 'Finished' THEN 0
                            ELSE g2.tonnage
                        END
                    )
                    FROM geology_ore_productions g2
                    WHERE g2.tgl_production < make_date(%s, 1, 1)
                      {g2_iup_clause}
                ), 0)
                -
                COALESCE((
                    SELECT SUM(
                        CASE
                            WHEN s2.sale_dome = 'Finished' THEN 0
                            ELSE s2.tonnage
                        END
                    )
                    FROM selling_barging s2
                    WHERE s2.date_hauling < make_date(%s, 1, 1)
                      AND s2.status_barging = 'Complete'
                      {s2_iup_clause}
                ), 0) AS opening_balance
        )
        SELECT
            b.dt,
            b.bulan_label,
            COALESCE(i.total_in, 0) AS total_in,
            COALESCE(o.total_out, 0) AS total_out,
            sa.opening_balance,
            sa.opening_balance
            + SUM(
                COALESCE(i.in_stock, 0) - COALESCE(o.out_stock, 0)
              ) OVER (
                ORDER BY b.dt
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
              ) AS running_balance
        FROM bulan b
        LEFT JOIN incoming i ON b.dt = i.dt
        LEFT JOIN outgoing o ON b.dt = o.dt
        CROSS JOIN saldo_awal sa
        ORDER BY b.dt
    """

    params = (
        [year, year, year] + g_iup_params +
        [year] + s_iup_params +
        [year] + g2_iup_params +
        [year] + s2_iup_params
    )

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    summary = {
        "opening_balance": rows[0]["opening_balance"] if rows else 0,
        "total_in": sum(r["total_in"] or 0 for r in rows),
        "total_out": sum(r["total_out"] or 0 for r in rows),
        "closing_balance": rows[-1]["running_balance"] if rows else 0,
    }

    return {"rows": rows, "summary": summary}

def fetch_inventory_dome_year(year: int, iup_filter=None):
    p_iup_clause, p_iup_params = build_iup_clause(iup_filter, "p")
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")

    query = f"""
        WITH prod AS (
            SELECT
                TRIM(p.stockpile) AS stockpile,
                TRIM(p.pile_id) AS pile_id,
                TRIM(p.nama_material) AS nama_material,
                SUM(p.tonnage) AS total_ore,
                SUM(
                    CASE
                        WHEN p.roa_ni IS NOT NULL AND p.sample_number IS NOT NULL THEN p.tonnage
                        ELSE 0
                    END
                ) AS released,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_ni) / NULLIF(SUM(
                    CASE WHEN p.sample_number IS NOT NULL AND p.roa_ni IS NOT NULL THEN p.tonnage END
                ), 0), 0)::numeric, 2) AS ni,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_co) / NULLIF(SUM(
                    CASE WHEN p.sample_number IS NOT NULL AND p.roa_co IS NOT NULL THEN p.tonnage END
                ), 0), 0)::numeric, 2) AS co,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_fe) / NULLIF(SUM(
                    CASE WHEN p.sample_number IS NOT NULL AND p.roa_fe IS NOT NULL THEN p.tonnage END
                ), 0), 0)::numeric, 2) AS fe,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_mgo) / NULLIF(SUM(
                    CASE WHEN p.sample_number IS NOT NULL AND p.roa_mgo IS NOT NULL THEN p.tonnage END
                ), 0), 0)::numeric, 2) AS mgo,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_sio2) / NULLIF(SUM(
                    CASE WHEN p.sample_number IS NOT NULL AND p.roa_sio2 IS NOT NULL THEN p.tonnage END
                ), 0), 0)::numeric, 2) AS sio2,
                ROUND(
                    COALESCE(
                        (SUM(p.tonnage * p.roa_sio2) / NULLIF(SUM(
                            CASE WHEN p.sample_number IS NOT NULL AND p.roa_sio2 IS NOT NULL THEN p.tonnage END
                        ), 0)) /
                        (
                            (SUM(p.tonnage * p.roa_mgo) / NULLIF(SUM(
                                CASE WHEN p.sample_number IS NOT NULL AND p.roa_mgo IS NOT NULL THEN p.tonnage END
                            ), 0)) + 0.000001
                        ),
                        0
                    )::numeric, 2
                ) AS sm
            FROM view_geology_ore_details_roa p
            WHERE p.status_dome != 'Finished'
              AND p.direct = 'No'
              AND EXTRACT(YEAR FROM p.tgl_production) <= %s
              {p_iup_clause}
            GROUP BY p.stockpile, p.pile_id, p.nama_material
        ),
        sell AS (
            SELECT
                TRIM(s.stockpile) AS stockpile,
                TRIM(s.dome) AS pile_id,
                TRIM(s.material) AS nama_material,
                SUM(s.tonnage) AS tonnage
            FROM view_selling_details s
            WHERE EXTRACT(YEAR FROM s.date_barge_out) <= %s
              AND s.status_barging = 'Complete'
              {s_iup_clause}
            GROUP BY s.stockpile, s.dome, s.material
        )
        SELECT 
            p.stockpile,
            p.pile_id,
            p.nama_material,
            p.total_ore,
            p.released,
            COALESCE(ROUND(SUM(
                CASE
                    WHEN p.nama_material = 'LIM' AND s.nama_material = 'SAP' THEN s.tonnage
                    WHEN p.nama_material = 'SAP' AND s.nama_material = 'LIM' THEN s.tonnage
                    WHEN p.nama_material = s.nama_material THEN s.tonnage
                    ELSE 0
                END
            )::numeric, 2), 0) AS total_selling,
            ROUND((
                p.total_ore - COALESCE(SUM(
                    CASE
                        WHEN p.nama_material = 'LIM' AND s.nama_material = 'SAP' THEN s.tonnage
                        WHEN p.nama_material = 'SAP' AND s.nama_material = 'LIM' THEN s.tonnage
                        WHEN p.nama_material = s.nama_material THEN s.tonnage
                        ELSE 0
                    END
                ), 0)
            )::numeric, 2) AS balance,
            p.ni, p.co, p.fe, p.mgo, p.sio2, p.sm
        FROM prod p
        LEFT JOIN sell s
          ON p.stockpile = s.stockpile
         AND p.pile_id = s.pile_id
        GROUP BY
            p.stockpile, p.pile_id, p.nama_material,
            p.total_ore, p.released,
            p.ni, p.co, p.fe, p.mgo, p.sio2, p.sm
        ORDER BY p.nama_material, p.stockpile
    """

    params = [year] + p_iup_params + [year] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}