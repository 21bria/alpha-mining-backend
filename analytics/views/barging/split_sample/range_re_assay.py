from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import datetime
from django.db import connection
from django.utils.html import escape
import json,re
from analytics.services.iup_filter import build_iup_clause
# Fungsi untuk sanitasi input
def sanitize_input(value):
    if value is None:
        return None
    return escape(re.sub(r"[;'\"]", "", str(value)))

def samplesReAssaySummary(request):
    data = get_samples_re_assay_summary(
        iup_filter=request.GET.get("iup_id") or request.GET.get("iup_filter"),
        typeFilter=request.GET.get("typeFilter"),
        startDate=request.GET.get("startDate"),
        endDate=request.GET.get("endDate"),
        bulanFilter=request.GET.get("bulanFilter"),
        tahunFilter=request.GET.get("tahunFilter")
    )
    return JsonResponse({"data": data}, safe=False)

def get_samples_re_assay_summary(
    typeFilter=None,
    startDate=None,
    endDate=None,
    bulanFilter=None,
    tahunFilter=None,
    iup_filter=None
):
    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")

    sql_query = f"""
       SELECT 
            t1.iup_id,
            t1.date_barge_out,
            TRIM(t1.barge_name) AS barge_name,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(
                SUM(t1.tonnage * t1.ni) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS ni_split,
            COALESCE(
                SUM(t1.tonnage * t1.fe) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS fe_split,
            COALESCE(
                SUM(t1.tonnage * t1.sm) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS sm_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni, 0) AS ni_official,
            COALESCE(t2.fe, 0) AS fe_official,
            COALESCE(t2.sm, 0) AS sm_official,
            COALESCE(
                (
                    SUM(t1.tonnage * t1.ni) /
                    NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                ) - t2.ni,
                0
            ) AS ni_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.ni) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.ni
                ) / NULLIF(t2.ni, 0) * 100,
                0
            ) AS ni_diff_perc,
            COALESCE(
                (
                    SUM(t1.tonnage * t1.fe) /
                    NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                ) - t2.fe,
                0
            ) AS fe_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.fe) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.fe
                ) / NULLIF(t2.fe, 0) * 100,
                0
            ) AS fe_diff_perc,
            COALESCE(
                (
                    SUM(t1.tonnage * t1.sm) /
                    NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                ) - t2.sm,
                0
            ) AS sm_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.sm) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.sm
                ) / NULLIF(t2.sm, 0) * 100,
                0
            ) AS sm_diff_perc,
            COALESCE(t2.re_assay, 0) AS re_assay
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT 
                iup_id,
                product_code,
                type_selling,
                tonnage_official,
                ni,
                fe,
                sm,
                re_assay
            FROM (
                SELECT 
                    iup_id,
                    product_code,
                    type_selling,
                    COALESCE(SUM(tonnage), 0) AS tonnage_official,
                    COALESCE(SUM(ni), 0) AS ni,
                    COALESCE(SUM(fe), 0) AS fe,
                    COALESCE(SUM(sm), 0) AS sm,
                    re_assay,
                    ROW_NUMBER() OVER(
                        PARTITION BY iup_id, product_code
                        ORDER BY re_assay DESC
                    ) AS rn
                FROM view_selling_official
                GROUP BY iup_id, product_code, type_selling, re_assay
            ) x
            WHERE rn = 1
        ) AS t2
            ON t1.iup_id = t2.iup_id
           AND t1.code_lot = t2.product_code
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
        sql_query += " AND EXTRACT(MONTH FROM t1.date_barge_out) = %s AND EXTRACT(YEAR FROM t1.date_barge_out) = %s"
        params.extend([bulanFilter, tahunFilter])
    elif tahunFilter:
        sql_query += " AND EXTRACT(YEAR FROM t1.date_barge_out) = %s"
        params.append(tahunFilter)

    sql_query += """
        GROUP BY 
            t1.iup_id, t1.date_barge_out, t1.code_lot, t1.barge_code, t1.barge_name,
            t2.tonnage_official, t2.ni, t2.fe, t2.sm, t2.re_assay
        ORDER BY t1.code_lot ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return sql_data
