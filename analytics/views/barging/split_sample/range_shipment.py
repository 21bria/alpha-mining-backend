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

def shipmentSummaryBuyer(request):
    data = get_shipment_summary_buyer(
        iup_filter=request.GET.get("iup_id") or request.GET.get("iup_filter"),
        typeFilter=request.GET.get("typeFilter"),
        startDate=request.GET.get("startDate"),
        endDate=request.GET.get("endDate"),
        bulanFilter=request.GET.get("bulanFilter"),
        tahunFilter=request.GET.get("tahunFilter")
    )
    return JsonResponse({"data": data}, safe=False)


def get_shipment_summary_buyer(
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
            TRIM(t1.factory_stock) AS buyer,
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
            ) AS sm_diff_perc
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT 
                iup_id,
                product_code,
                tonnage_official,
                ni,
                fe,
                sm,
                type_selling
            FROM (
                SELECT
                    iup_id,
                    product_code,
                    type_selling,
                    COALESCE(SUM(tonnage), 0) AS tonnage_official,
                    COALESCE(SUM(ni), 0) AS ni,
                    COALESCE(SUM(fe), 0) AS fe,
                    COALESCE(SUM(sm), 0) AS sm,
                    ROW_NUMBER() OVER(
                        PARTITION BY iup_id, product_code
                        ORDER BY re_assay DESC NULLS LAST
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
            t1.iup_id, t1.factory_stock, t1.date_barge_out, t1.code_lot, t1.barge_code, t1.barge_name,
            t2.tonnage_official, t2.ni, t2.fe, t2.sm
        ORDER BY t1.code_lot ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return sql_data


def get_shipment_summary_month(startDate=None, endDate=None, iup_filter=None):
    tahun = None
    if endDate:
        try:
            tahun = datetime.strptime(endDate, "%Y-%m-%d").year
        except Exception:
            tahun = None

    s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")

    sql_query = f"""
      WITH split_data AS (
            SELECT
                iup_id,
                TRIM(factory_stock) AS buyer,
                EXTRACT(YEAR FROM date_barge_out)::int AS year,
                EXTRACT(MONTH FROM date_barge_out)::int AS month,
                TO_CHAR(date_barge_out, 'Mon') AS month_name,
                TRIM(type_selling) AS type_selling,
                COUNT(DISTINCT barge_code) AS total_barge,
                SUM(tonnage) AS tonnage_split,
                SUM(tonnage * ni) / NULLIF(SUM(CASE WHEN ni IS NOT NULL THEN tonnage ELSE 0 END), 0) AS ni_split,
                SUM(tonnage * fe) / NULLIF(SUM(CASE WHEN fe IS NOT NULL THEN tonnage ELSE 0 END), 0) AS fe_split,
                SUM(tonnage * sm) / NULLIF(SUM(CASE WHEN sm IS NOT NULL THEN tonnage ELSE 0 END), 0) AS sm_split
            FROM view_selling_split_barge
            GROUP BY
                iup_id,
                TRIM(factory_stock),
                EXTRACT(YEAR FROM date_barge_out),
                EXTRACT(MONTH FROM date_barge_out),
                TO_CHAR(date_barge_out, 'Mon'),
                TRIM(type_selling)
        ),
        reassy_official AS (
            SELECT
                iup_id,
                TRIM(factory_stock) AS buyer,
                EXTRACT(YEAR FROM end_date)::int AS year,
                EXTRACT(MONTH FROM end_date)::int AS month,
                TRIM(type_selling) AS type_selling,
                product_code,
                tonnage,
                ni,
                fe,
                sm,
                ROW_NUMBER() OVER(
                    PARTITION BY
                        iup_id,
                        TRIM(factory_stock),
                        EXTRACT(YEAR FROM end_date),
                        EXTRACT(MONTH FROM end_date),
                        TRIM(type_selling),
                        product_code
                    ORDER BY re_assay DESC NULLS LAST
                ) AS rn
            FROM view_selling_official
        ),
        official_data AS (
            SELECT
                iup_id,
                buyer,
                year,
                month,
                type_selling,
                SUM(tonnage) AS tonnage_official,
                SUM(tonnage * ni) / NULLIF(SUM(CASE WHEN ni IS NOT NULL THEN tonnage ELSE 0 END), 0) AS ni_official,
                SUM(tonnage * fe) / NULLIF(SUM(CASE WHEN fe IS NOT NULL THEN tonnage ELSE 0 END), 0) AS fe_official,
                SUM(tonnage * sm) / NULLIF(SUM(CASE WHEN sm IS NOT NULL THEN tonnage ELSE 0 END), 0) AS sm_official
            FROM reassy_official
            WHERE rn = 1
            GROUP BY
                iup_id,
                buyer,
                year,
                month,
                type_selling
        )
        SELECT
            s.iup_id,
            s.buyer,
            s.year,
            s.month,
            s.month_name,
            s.type_selling,
            s.total_barge,
            s.tonnage_split,
            s.ni_split,
            s.fe_split,
            s.sm_split,
            COALESCE(o.tonnage_official, 0) AS tonnage_official,
            COALESCE(o.ni_official, 0) AS ni_official,
            COALESCE(o.fe_official, 0) AS fe_official,
            COALESCE(o.sm_official, 0) AS sm_official,
            s.ni_split - COALESCE(o.ni_official, 0) AS ni_diff,
            (s.ni_split - COALESCE(o.ni_official, 0)) / NULLIF(o.ni_official, 0) * 100 AS ni_diff_perc,
            s.fe_split - COALESCE(o.fe_official, 0) AS fe_diff,
            (s.fe_split - COALESCE(o.fe_official, 0)) / NULLIF(o.fe_official, 0) * 100 AS fe_diff_perc,
            s.sm_split - COALESCE(o.sm_official, 0) AS sm_diff,
            (s.sm_split - COALESCE(o.sm_official, 0)) / NULLIF(o.sm_official, 0) * 100 AS sm_diff_perc
        FROM split_data s
        LEFT JOIN official_data o
            ON s.iup_id = o.iup_id
           AND s.buyer = o.buyer
           AND s.year = o.year
           AND s.month = o.month
           AND s.type_selling = o.type_selling
        WHERE 1=1
        {s_iup_clause}
    """

    params = []
    params.extend(s_iup_params)

    if tahun:
        sql_query += " AND s.year = %s"
        params.append(tahun)

    sql_query += """
       ORDER BY s.month, s.buyer, s.type_selling
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = []
        for row in cursor.fetchall():
            clean = {}
            for key, val in zip(columns, row):
                clean[key] = 0 if val is None else val
            sql_data.append(clean)

    return sql_data