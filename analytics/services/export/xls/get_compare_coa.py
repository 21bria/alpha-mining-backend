
# reports/services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_official_split(ds: str, de: str, material: str = None, iup_filter=None):
    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")

    sql_query = f"""
        SELECT 
            t1.date_barge_in,
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            TRIM(t1.barge_name) AS barge_name,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(
                SUM(t1.tonnage * t1.ni) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS ni_split,
            COALESCE(
                SUM(t1.tonnage * t1.fe) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS fe_split,
            COALESCE(
                SUM(t1.tonnage * t1.mgo) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS mgo_split,
            COALESCE(
                SUM(t1.tonnage * t1.sio2) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS sio2_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni_official, 0) AS ni_official,
            COALESCE(t2.fe_official, 0) AS fe_official, 
            COALESCE(t2.mgo_official, 0) AS mgo_official,
            COALESCE(t2.sio2_official, 0) AS sio2_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.ni) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage END), 0))
                    - t2.ni_official
                ) / NULLIF(t2.ni_official, 0) * 100,
                0
            ) AS ni_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.fe) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage END), 0))
                    - t2.fe_official
                ) / NULLIF(t2.fe_official, 0) * 100,
                0
            ) AS fe_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.mgo) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage END), 0))
                    - t2.mgo_official
                ) / NULLIF(t2.mgo_official, 0) * 100,
                0
            ) AS mgo_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage END), 0))
                    - t2.sio2_official
                ) / NULLIF(t2.sio2_official, 0) * 100,
                0
            ) AS sio2_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT 
                product_code,
                tonnage AS tonnage_official,
                ni AS ni_official,
                fe AS fe_official,
                mgo AS mgo_official,
                sio2 AS sio2_official,
                sm AS sm_official,
                type_selling,
                re_assay
            FROM (
                SELECT 
                    id,
                    product_code,
                    tonnage,
                    ni,
                    fe,
                    mgo,
                    sio2,
                    sm,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
            ) z
            WHERE rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE t1.date_barge_out BETWEEN %s AND %s
        {t1_iup_clause}
    """

    params = [ds, de] + t1_iup_params

    if material:
        sql_query += " AND t1.sale_adjust = %s"
        params.append(material)

    sql_query += """
        GROUP BY
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t1.barge_name,
            t2.tonnage_official,
            t2.ni_official,
            t2.fe_official,
            t2.mgo_official,
            t2.sio2_official
        ORDER BY t1.date_barge_in ASC
    """

    with connection.cursor() as cur:
        cur.execute(sql_query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}

def fetch_official_split_year(year: int, material: str = None, iup_filter=None):
    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")

    sql_query = f"""
        SELECT 
            t1.date_barge_in,
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            TRIM(t1.barge_name) AS barge_name,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(
                SUM(t1.tonnage * t1.ni) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS ni_split,
            COALESCE(
                SUM(t1.tonnage * t1.fe) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS fe_split,
            COALESCE(
                SUM(t1.tonnage * t1.mgo) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS mgo_split,
            COALESCE(
                SUM(t1.tonnage * t1.sio2) / NULLIF(
                    SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END),
                    0
                ),
                0
            ) AS sio2_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni_official, 0) AS ni_official,
            COALESCE(t2.fe_official, 0) AS fe_official,
            COALESCE(t2.mgo_official, 0) AS mgo_official,
            COALESCE(t2.sio2_official, 0) AS sio2_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.ni) / NULLIF(
                        SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage END), 0
                    ))
                    - t2.ni_official
                ) / NULLIF(t2.ni_official, 0) * 100,
                0
            ) AS ni_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.fe) / NULLIF(
                        SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage END), 0
                    ))
                    - t2.fe_official
                ) / NULLIF(t2.fe_official, 0) * 100,
                0
            ) AS fe_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.mgo) / NULLIF(
                        SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage END), 0
                    ))
                    - t2.mgo_official
                ) / NULLIF(t2.mgo_official, 0) * 100,
                0
            ) AS mgo_diff,
            COALESCE(
                (
                    (SUM(t1.tonnage * t1.sio2) / NULLIF(
                        SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage END), 0
                    ))
                    - t2.sio2_official
                ) / NULLIF(t2.sio2_official, 0) * 100,
                0
            ) AS sio2_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT 
                product_code,
                tonnage AS tonnage_official,
                ni AS ni_official,
                fe AS fe_official,
                mgo AS mgo_official,
                sio2 AS sio2_official,
                sm AS sm_official,
                type_selling,
                re_assay
            FROM (
                SELECT 
                    id,
                    product_code,
                    tonnage,
                    ni,
                    fe,
                    mgo,
                    sio2,
                    sm,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
            ) z
            WHERE rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE EXTRACT(YEAR FROM t1.date_barge_out) = %s
        {t1_iup_clause}
    """

    params = [year] + t1_iup_params

    if material:
        sql_query += " AND t1.sale_adjust = %s"
        params.append(material)

    sql_query += """
        GROUP BY
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t1.barge_name,
            t2.tonnage_official,
            t2.ni_official,
            t2.fe_official,
            t2.mgo_official,
            t2.sio2_official
        ORDER BY t1.date_barge_in ASC
    """

    with connection.cursor() as cur:
        cur.execute(sql_query, params)
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    return {"rows": rows}