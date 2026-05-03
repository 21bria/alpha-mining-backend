
# /services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def g(row, key):
    return row.get(key, 0) or 0

def fetch_inventory_balance(ds: str, de: str, iup_filter=None):
    g_iup_clause, g_iup_params = build_iup_clause(iup_filter, "g")
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")
    g2_iup_clause, g2_iup_params = build_iup_clause(iup_filter, "g2")
    s2_iup_clause, s2_iup_params = build_iup_clause(iup_filter, "s2")

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS dt
        ),
        incoming AS (
            SELECT
                g.tgl_production::date AS dt,
                SUM(g.tonnage) AS total_in,
                SUM(
                    CASE
                        WHEN g.status_dome = 'Finished' THEN 0
                        ELSE g.tonnage
                    END
                ) AS in_stock
            FROM geology_ore_productions g
            WHERE g.tgl_production BETWEEN %s AND %s
              {g_iup_clause}
            GROUP BY g.tgl_production::date
        ),
        outgoing AS (
            SELECT
                s.date_hauling::date AS dt,
                SUM(s.tonnage) AS total_out,
                SUM(
                    CASE
                        WHEN s.sale_dome = 'Finished' THEN 0
                        ELSE s.tonnage
                    END
                ) AS out_stock
            FROM selling_barging s
            WHERE s.date_hauling BETWEEN %s AND %s
              AND s.status_barging = 'Complete'
              {s_iup_clause}
            GROUP BY s.date_hauling::date
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
                    WHERE g2.tgl_production < %s
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
                    WHERE s2.date_hauling < %s
                      AND s2.status_barging = 'Complete'
                      {s2_iup_clause}
                ), 0) AS opening_balance
        )
        SELECT
            t.dt,
            COALESCE(i.total_in, 0) AS total_in,
            COALESCE(o.total_out, 0) AS total_out,
            sa.opening_balance,
            sa.opening_balance
            + SUM(
                COALESCE(i.in_stock, 0) - COALESCE(o.out_stock, 0)
              ) OVER (
                ORDER BY t.dt
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
              ) AS running_balance
        FROM tanggal t
        LEFT JOIN incoming i ON t.dt = i.dt
        LEFT JOIN outgoing o ON t.dt = o.dt
        CROSS JOIN saldo_awal sa
        ORDER BY t.dt
    """

    params = (
        [ds, de, ds, de] + g_iup_params +
        [ds, de] + s_iup_params +
        [ds] + g2_iup_params +
        [ds] + s2_iup_params
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

def fetch_inventory_dome(de: str, iup_filter=None):
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
                ) AS sm,
                p.direct
            FROM view_geology_ore_details_roa p
            WHERE p.status_dome != 'Finished'
              AND p.direct = 'No'
              AND p.tgl_production <= %s
              {p_iup_clause}
            GROUP BY p.stockpile, p.pile_id, p.nama_material, p.direct
        ),
        sell AS (
            SELECT
                TRIM(s.stockpile) AS stockpile,
                TRIM(s.dome) AS pile_id,
                TRIM(s.material) AS name,
                SUM(s.tonnage) AS tonnage
            FROM view_selling_details s
            WHERE s.date_barge_out <= %s
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
                    WHEN p.nama_material = 'LIM' AND s.name = 'SAP' THEN s.tonnage
                    WHEN p.nama_material = 'SAP' AND s.name = 'LIM' THEN s.tonnage
                    WHEN p.nama_material = s.name THEN s.tonnage
                    ELSE 0
                END
            )::numeric, 2), 0) AS total_selling,
            ROUND((
                p.total_ore - COALESCE(SUM(
                    CASE
                        WHEN p.nama_material = 'LIM' AND s.name = 'SAP' THEN s.tonnage
                        WHEN p.nama_material = 'SAP' AND s.name = 'LIM' THEN s.tonnage
                        WHEN p.nama_material = s.name THEN s.tonnage
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

    params = [de] + p_iup_params + [de] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}