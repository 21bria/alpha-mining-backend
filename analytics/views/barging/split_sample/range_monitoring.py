from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.utils.html import escape
import json,re
from analytics.services.iup_filter import build_iup_clause
# Fungsi untuk sanitasi input
def sanitize_input(value):
    if value is None:
        return None
    return escape(re.sub(r"[;'\"]", "", str(value)))

def clean_value(v):
    if v is None:
        return None
    try:
        if isinstance(v, float) and (v != v):  # NaN check
            return None
        return v
    except:
        return None
    

def samplesMonitoring(request):
    data = get_samples_data(
        iup_filter=request.GET.get("iup_id") or request.GET.get("iup_filter"),
        typeFilter=request.GET.get("typeFilter"),
        startDate=request.GET.get("startDate"),
        endDate=request.GET.get("endDate"),
        codeFilter=json.loads(request.GET.get("codeFilter", "[]")),
        bulanFilter=request.GET.get("bulanFilter"),
        tahunFilter=request.GET.get("tahunFilter")
    )
    return JsonResponse({"data": data}, safe=False)


def get_samples_data(
    typeFilter=None,
    startDate=None,
    endDate=None,
    codeFilter=None,
    bulanFilter=None,
    tahunFilter=None,
    iup_filter=None,
):
    codeFilter = codeFilter or []
    codeFilter = [sanitize_input(code) for code in codeFilter if code]

    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")

    sql_query = f"""
       SELECT 
            t1.iup_id,
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,

            -- Tonnage dan grade dari monitoring
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_monitoring,
            COALESCE(
                SUM(t1.tonnage * t1.ni) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS ni_monitoring,
            COALESCE(
                SUM(t1.tonnage * t1.co) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.co IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS co_monitoring,
            COALESCE(
                SUM(t1.tonnage * t1.fe) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS fe_monitoring,
            COALESCE(
                SUM(t1.tonnage * t1.mgo) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS mgo_monitoring,
            COALESCE(
                SUM(t1.tonnage * t1.sio2) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS sio2_monitoring,

            -- Split
            COALESCE(t4.tonnage_split, 0) AS tonnage_split,
            COALESCE(t4.ni_split, 0) AS ni_split,
            COALESCE(t4.co_split, 0) AS co_split,
            COALESCE(t4.fe_split, 0) AS fe_split,
            COALESCE(t4.mgo_split, 0) AS mgo_split,
            COALESCE(t4.sio2_split, 0) AS sio2_split,

            -- Official
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni, 0) AS ni_official,
            COALESCE(t2.co, 0) AS co_official,
            COALESCE(t2.fe, 0) AS fe_official,
            COALESCE(t2.mgo, 0) AS mgo_official,
            COALESCE(t2.sio2, 0) AS sio2_official,
            t2.re_assay,

            -- Plan
            COALESCE(t3.tonnage_plan, 0) AS tonnage_plan,
            COALESCE(t3.ni_plan, 0) AS ni_plan,
            COALESCE(t3.co_plan, 0) AS co_plan,
            COALESCE(t3.fe_plan, 0) AS fe_plan,
            COALESCE(t3.mgo_plan, 0) AS mgo_plan,
            COALESCE(t3.sio2_plan, 0) AS sio2_plan

        FROM view_selling_monitoring t1

        LEFT JOIN (
            SELECT
                iup_id,
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(ni), 0) AS ni,
                COALESCE(SUM(co), 0) AS co,
                COALESCE(SUM(fe), 0) AS fe,
                COALESCE(SUM(mgo), 0) AS mgo,
                COALESCE(SUM(sio2), 0) AS sio2,
                type_selling,
                re_assay
            FROM view_selling_official
            GROUP BY iup_id, product_code, type_selling, re_assay
        ) AS t2
            ON t1.iup_id = t2.iup_id
           AND t1.code_lot = t2.product_code

        LEFT JOIN (
            SELECT
                iup_id,
                code,
                COALESCE(SUM(tonnage), 0) AS tonnage_plan,
                COALESCE(SUM(ni), 0) AS ni_plan,
                COALESCE(SUM(co), 0) AS co_plan,
                COALESCE(SUM(fe), 0) AS fe_plan,
                COALESCE(SUM(mgo), 0) AS mgo_plan,
                COALESCE(SUM(sio2), 0) AS sio2_plan
            FROM master_selling_code
            GROUP BY iup_id, code
        ) AS t3
            ON t1.iup_id = t3.iup_id
           AND t1.code_lot = t3.code

        LEFT JOIN (
            SELECT 
                iup_id,
                code_lot,
                barge_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_split,
                COALESCE(
                    SUM(tonnage * ni) /
                    NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND ni IS NOT NULL THEN tonnage ELSE 0 END), 0),
                    0
                ) AS ni_split,
                COALESCE(
                    SUM(tonnage * co) /
                    NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND co IS NOT NULL THEN tonnage ELSE 0 END), 0),
                    0
                ) AS co_split,
                COALESCE(
                    SUM(tonnage * fe) /
                    NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND fe IS NOT NULL THEN tonnage ELSE 0 END), 0),
                    0
                ) AS fe_split,
                COALESCE(
                    SUM(tonnage * mgo) /
                    NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND mgo IS NOT NULL THEN tonnage ELSE 0 END), 0),
                    0
                ) AS mgo_split,
                COALESCE(
                    SUM(tonnage * sio2) /
                    NULLIF(SUM(CASE WHEN sample_number IS NOT NULL AND sio2 IS NOT NULL THEN tonnage ELSE 0 END), 0),
                    0
                ) AS sio2_split
            FROM view_selling_split_barge
            GROUP BY iup_id, code_lot, barge_code
        ) AS t4
            ON t1.iup_id = t4.iup_id
           AND t1.code_lot = t4.code_lot
           AND t1.barge_code = t4.barge_code

        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t1_iup_params)

    if typeFilter:
        sql_query += " AND t1.sale_adjust = %s"
        params.append(typeFilter)

    if startDate and endDate:
        sql_query += " AND t1.date_hauling BETWEEN %s AND %s"
        params.extend([startDate, endDate])

    if bulanFilter and tahunFilter:
        sql_query += """
            AND EXTRACT(MONTH FROM t1.date_barge_out) = %s
            AND EXTRACT(YEAR FROM t1.date_barge_out) = %s
        """
        params.extend([bulanFilter, tahunFilter])
    elif tahunFilter:
        sql_query += " AND EXTRACT(YEAR FROM t1.date_barge_out) = %s"
        params.append(tahunFilter)

    if codeFilter:
        placeholders = ", ".join(["%s"] * len(codeFilter))
        sql_query += f" AND t1.code_lot IN ({placeholders})"
        params.extend(codeFilter)

    sql_query += """
        GROUP BY 
            t1.iup_id,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.ni,
            t2.co,
            t2.fe,
            t2.mgo,
            t2.sio2,
            t2.re_assay,
            t3.tonnage_plan,
            t3.ni_plan,
            t3.co_plan,
            t3.fe_plan,
            t3.mgo_plan,
            t3.sio2_plan,
            t4.tonnage_split,
            t4.ni_split,
            t4.co_split,
            t4.fe_split,
            t4.mgo_split,
            t4.sio2_split
        ORDER BY t1.code_lot, t2.re_assay ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    grouped = {}
    for row in sql_data:
        row = {k: clean_value(v) for k, v in row.items()}
        key = (row["iup_id"], row["code_lot"], row["barge_code"])

        if key not in grouped:
            grouped[key] = {
                "iup_id": row["iup_id"],
                "code_lot": row["code_lot"],
                "barge_code": row["barge_code"],
                "lot_barge": row.get("lot_barge"),
                "tonnage_monitoring": row.get("tonnage_monitoring"),
                "tonnage_split": row.get("tonnage_split"),
                "tonnage_official": row.get("tonnage_official"),
                "tonnage_plan": row.get("tonnage_plan"),
                "ni_plan": row.get("ni_plan"),
                "ni_monitoring": row.get("ni_monitoring"),
                "ni_split": row.get("ni_split"),
                "fe_plan": row.get("fe_plan"),
                "fe_monitoring": row.get("fe_monitoring"),
                "fe_split": row.get("fe_split"),
                "co_plan": row.get("co_plan"),
                "co_monitoring": row.get("co_monitoring"),
                "co_split": row.get("co_split"),
                "mgo_plan": row.get("mgo_plan"),
                "mgo_monitoring": row.get("mgo_monitoring"),
                "mgo_split": row.get("mgo_split"),
                "sio2_plan": row.get("sio2_plan"),
                "sio2_monitoring": row.get("sio2_monitoring"),
                "sio2_split": row.get("sio2_split"),
                "officials": []
            }

        grouped[key]["officials"].append({
            "re_assay": row.get("re_assay"),
            "ni": row.get("ni_official"),
            "fe": row.get("fe_official"),
            "co": row.get("co_official"),
            "mgo": row.get("mgo_official"),
            "sio2": row.get("sio2_official"),
        })

    final_data = list(grouped.values())
    return final_data