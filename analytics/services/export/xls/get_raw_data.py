
# reports/services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def export_production_mining(ds: str, de: str, iup_filter=None):
    v_iup_clause, v_iup_params = build_iup_clause(iup_filter, "v")

    query = f"""
        SELECT *
        FROM view_mining_productions v
        WHERE v.date_production BETWEEN %s AND %s
        {v_iup_clause}
        ORDER BY v.date_production::date
    """

    params = [ds, de] + v_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}


def export_production_quality(ds: str, de: str, iup_filter=None):
    op_iup_clause, op_iup_params = build_iup_clause(iup_filter, "op")

    query = f"""
        SELECT *
        FROM view_geology_ore_production op
        WHERE op.tgl_production BETWEEN %s AND %s
        {op_iup_clause}
        ORDER BY op.tgl_production::date
    """

    params = [ds, de] + op_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}


def export_selling_quality(ds: str, de: str, iup_filter=None):
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")

    query = f"""
        SELECT *
        FROM view_selling_details s
        WHERE s.date_barge_in >= %s
          AND s.date_barge_out <= %s
          AND s.status_barging = 'Complete'
          {s_iup_clause}
        ORDER BY s.date_barge_out::date
    """

    params = [ds, de] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}


def export_inventory_dome(de: str, iup_filter=None):
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
                ROUND(
                    COALESCE(
                        SUM(p.tonnage * p.roa_ni) / NULLIF(SUM(
                            CASE
                                WHEN p.sample_number IS NOT NULL AND p.roa_ni IS NOT NULL THEN p.tonnage
                                ELSE 0
                            END
                        ), 0),
                        0
                    )::numeric, 2
                ) AS ni,
                ROUND(
                    COALESCE(
                        SUM(p.tonnage * p.roa_co) / NULLIF(SUM(
                            CASE
                                WHEN p.sample_number IS NOT NULL AND p.roa_co IS NOT NULL THEN p.tonnage
                                ELSE 0
                            END
                        ), 0),
                        0
                    )::numeric, 2
                ) AS co,
                ROUND(
                    COALESCE(
                        SUM(p.tonnage * p.roa_fe) / NULLIF(SUM(
                            CASE
                                WHEN p.sample_number IS NOT NULL AND p.roa_fe IS NOT NULL THEN p.tonnage
                                ELSE 0
                            END
                        ), 0),
                        0
                    )::numeric, 2
                ) AS fe,
                ROUND(
                    COALESCE(
                        SUM(p.tonnage * p.roa_mgo) / NULLIF(SUM(
                            CASE
                                WHEN p.sample_number IS NOT NULL AND p.roa_mgo IS NOT NULL THEN p.tonnage
                                ELSE 0
                            END
                        ), 0),
                        0
                    )::numeric, 2
                ) AS mgo,
                ROUND(
                    COALESCE(
                        SUM(p.tonnage * p.roa_sio2) / NULLIF(SUM(
                            CASE
                                WHEN p.sample_number IS NOT NULL AND p.roa_sio2 IS NOT NULL THEN p.tonnage
                                ELSE 0
                            END
                        ), 0),
                        0
                    )::numeric, 2
                ) AS sio2,
                ROUND(
                    COALESCE(
                        (
                            SUM(p.tonnage * p.roa_sio2) / NULLIF(SUM(
                                CASE
                                    WHEN p.sample_number IS NOT NULL AND p.roa_sio2 IS NOT NULL THEN p.tonnage
                                    ELSE 0
                                END
                            ), 0)
                        ) / (
                            (
                                SUM(p.tonnage * p.roa_mgo) / NULLIF(SUM(
                                    CASE
                                        WHEN p.sample_number IS NOT NULL AND p.roa_mgo IS NOT NULL THEN p.tonnage
                                        ELSE 0
                                    END
                                ), 0)
                            ) + 0.000001
                        ),
                        0
                    )::numeric, 2
                ) AS sm
            FROM view_geology_ore_details_roa p
            WHERE p.status_dome != 'Finished'
              AND p.direct = 'No'
              AND p.tgl_production <= %s
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
            COALESCE(
                ROUND(SUM(
                    CASE
                        WHEN p.nama_material = 'LIM' AND s.nama_material = 'SAP' THEN s.tonnage
                        WHEN p.nama_material = 'SAP' AND s.nama_material = 'LIM' THEN s.tonnage
                        WHEN p.nama_material = s.nama_material THEN s.tonnage
                        ELSE 0
                    END
                )::numeric, 2),
                0
            ) AS total_selling,
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
            p.ni,
            p.co,
            p.fe,
            p.mgo,
            p.sio2,
            p.sm
        FROM prod p
        LEFT JOIN sell s
            ON p.stockpile = s.stockpile
           AND p.pile_id = s.pile_id
        GROUP BY
            p.stockpile,
            p.pile_id,
            p.nama_material,
            p.total_ore,
            p.released,
            p.ni,
            p.co,
            p.fe,
            p.mgo,
            p.sio2,
            p.sm
        ORDER BY p.nama_material, p.stockpile
    """

    params = [de] + p_iup_params + [de] + s_iup_params

    with connection.cursor() as cur:
        cur.execute(query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}