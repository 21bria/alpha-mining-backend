
# reports/services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_summary_to_year(year: int, iup_filter=None):
    m_iup_clause, m_iup_params = build_iup_clause(iup_filter, "m")
    mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
    op_iup_clause, op_iup_params = build_iup_clause(iup_filter, "op")
    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")
    g_iup_clause, g_iup_params = build_iup_clause(iup_filter, "g")
    sb_iup_clause, sb_iup_params = build_iup_clause(iup_filter, "sb")
    g2_iup_clause, g2_iup_params = build_iup_clause(iup_filter, "g2")
    sb2_iup_clause, sb2_iup_params = build_iup_clause(iup_filter, "sb2")

    with connection.cursor() as cur:
        # === Mining (summary per tahun) ===
        mining_query = f"""
            WITH mining AS (
                SELECT 
                    SUM(CASE WHEN m.nama_material = 'LIM' THEN m.tonnage ELSE 0 END)::numeric AS lim,
                    SUM(CASE WHEN m.nama_material = 'SAP' THEN m.tonnage ELSE 0 END)::numeric AS sap,
                    SUM(CASE WHEN m.nama_material = 'Waste' THEN m.tonnage ELSE 0 END)::numeric AS waste,
                    SUM(CASE WHEN m.nama_material = 'Quarry' THEN m.tonnage ELSE 0 END)::numeric AS quarry,
                    SUM(CASE WHEN m.nama_material = 'Top Soil' THEN m.tonnage ELSE 0 END)::numeric AS topsoil,
                    SUM(CASE WHEN m.nama_material = 'OB' THEN m.tonnage ELSE 0 END)::numeric AS ob,
                    SUM(CASE WHEN m.nama_material = 'Ballast' THEN m.tonnage ELSE 0 END)::numeric AS ballast,
                    SUM(CASE WHEN m.nama_material = 'Biomass' THEN m.tonnage ELSE 0 END)::numeric AS biomass,
                    SUM(m.tonnage)::numeric AS total
                FROM view_mining_productions m
                WHERE EXTRACT(YEAR FROM m.date_production) = %s
                  {m_iup_clause}
            ),
            plan AS (
                SELECT
                    SUM(
                        COALESCE(mp.lim, 0) + COALESCE(mp.sap, 0) + COALESCE(mp.quarry, 0) + 
                        COALESCE(mp.topsoil, 0) + COALESCE(mp.ob, 0) + COALESCE(mp.ballast, 0) +
                        COALESCE(mp.biomass, 0) + COALESCE(mp.waste, 0)
                    )::numeric AS plan_total
                FROM mining_plan_productions mp
                WHERE EXTRACT(YEAR FROM mp.date_plan) = %s
                  {mp_iup_clause}
            )
            SELECT 
                COALESCE(m.lim, 0) AS lim_total,
                COALESCE(m.sap, 0) AS sap_total,
                COALESCE(m.waste, 0) AS waste_total,
                COALESCE(m.quarry, 0) AS quarry_total,
                COALESCE(m.topsoil, 0) AS topsoil_total,
                COALESCE(m.ob, 0) AS ob_total,
                COALESCE(m.ballast, 0) AS ballast_total,
                COALESCE(m.biomass, 0) AS biomass_total,
                COALESCE(m.total, 0) AS actual_total,
                COALESCE(p.plan_total, 0) AS plan_total
            FROM mining m
            CROSS JOIN plan p
        """
        mining_params = [year] + m_iup_params + [year] + mp_iup_params
        cur.execute(mining_query, mining_params)

        mining_row = cur.fetchone()
        mining = {
            "lim_total": mining_row[0] or 0,
            "sap_total": mining_row[1] or 0,
            "waste_total": mining_row[2] or 0,
            "quarry_total": mining_row[3] or 0,
            "topsoil_total": mining_row[4] or 0,
            "ob_total": mining_row[5] or 0,
            "ballast_total": mining_row[6] or 0,
            "biomass_total": mining_row[7] or 0,
            "actual_total": mining_row[8] or 0,
            "plan_total": mining_row[9] or 0,
        }

        mining["ore"] = (mining["lim_total"] or 0) + (mining["sap_total"] or 0)
        mining["non_ore"] = (
            (mining["waste_total"] or 0) +
            (mining["quarry_total"] or 0) +
            (mining["topsoil_total"] or 0) +
            (mining["ob_total"] or 0) +
            (mining["ballast_total"] or 0) +
            (mining["biomass_total"] or 0)
        )

        # === Quality ===
        quality_query = f"""
            SELECT
                SUM(op.tonnage) AS prod_total,
                SUM(CASE WHEN mm.name = 'LIM' THEN op.tonnage ELSE 0 END) AS prod_lim,
                SUM(CASE WHEN mm.name = 'SAP' THEN op.tonnage ELSE 0 END) AS prod_sap
            FROM geology_ore_productions op
            LEFT JOIN master_materials mm ON mm.id = op.id_material
            WHERE EXTRACT(YEAR FROM op.tgl_production) = %s
              {op_iup_clause}
        """
        quality_params = [year] + op_iup_params
        cur.execute(quality_query, quality_params)

        q_total, q_lim, q_sap = cur.fetchone()
        quality = {
            "total": q_total or 0,
            "lim": q_lim or 0,
            "sap": q_sap or 0,
        }

        # === Selling ===
        selling_query = f"""
            WITH actual AS (
                SELECT
                    SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END) AS lim,
                    SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END) AS sap,
                    SUM(s.tonnage) AS total
                FROM selling_barging s
                WHERE EXTRACT(YEAR FROM s.date_barge_out) = %s
                  AND s.status_barging = 'Complete'
                  {s_iup_clause}
            )
            SELECT
                COALESCE(a.lim, 0) AS actual_lim,
                COALESCE(a.sap, 0) AS actual_sap,
                COALESCE(a.total, 0) AS actual_total
            FROM actual a
        """
        selling_params = [year] + s_iup_params
        cur.execute(selling_query, selling_params)

        s_lim_actual, s_sap_actual, s_total_actual = cur.fetchone()
        selling = {
            "actual": s_total_actual or 0,
            "lim_actual": s_lim_actual or 0,
            "sap_actual": s_sap_actual or 0,
        }

        # === Inventory ===
        inventory_query = f"""
            WITH incoming AS (
                SELECT
                    SUM(
                        CASE
                            WHEN g.status_dome = 'Finished' THEN 0
                            ELSE g.tonnage
                        END
                    ) AS in_stock,
                    SUM(g.tonnage) AS total_in
                FROM geology_ore_productions g
                WHERE EXTRACT(YEAR FROM g.tgl_production) = %s
                  {g_iup_clause}
            ),
            outgoing AS (
                SELECT
                    SUM(
                        CASE
                            WHEN sb.sale_dome = 'Finished' THEN 0
                            ELSE sb.tonnage
                        END
                    ) AS out_stock,
                    SUM(sb.tonnage) AS total_out
                FROM selling_barging sb
                WHERE EXTRACT(YEAR FROM sb.date_barge_out) = %s
                  AND sb.status_barging = 'Complete'
                  {sb_iup_clause}
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
                        WHERE EXTRACT(YEAR FROM g2.tgl_production) < %s
                          {g2_iup_clause}
                    ), 0)
                    -
                    COALESCE((
                        SELECT SUM(
                            CASE
                                WHEN sb2.sale_dome = 'Finished' THEN 0
                                ELSE sb2.tonnage
                            END
                        )
                        FROM selling_barging sb2
                        WHERE EXTRACT(YEAR FROM sb2.date_barge_out) < %s
                          AND sb2.status_barging = 'Complete'
                          {sb2_iup_clause}
                    ), 0) AS opening_balance
            )
            SELECT
                sa.opening_balance
                + COALESCE(i.in_stock, 0)
                - COALESCE(o.out_stock, 0) AS current_stock,
                COALESCE(i.total_in, 0) AS total_in,
                COALESCE(o.total_out, 0) AS total_out
            FROM saldo_awal sa
            CROSS JOIN incoming i
            CROSS JOIN outgoing o
        """
        inventory_params = (
            [year] + g_iup_params +
            [year] + sb_iup_params +
            [year] + g2_iup_params +
            [year] + sb2_iup_params
        )
        cur.execute(inventory_query, inventory_params)

        current_stock, inv_in, inv_out = cur.fetchone()
        inventory = {
            "current_stock": current_stock or 0,
            "in": inv_in or 0,
            "out": inv_out or 0,
        }

    return {
        "mining": mining,
        "quality": quality,
        "selling": selling,
        "inventory": inventory,
    }