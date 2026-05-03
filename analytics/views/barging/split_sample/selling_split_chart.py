from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connections
from django.utils.html import escape
import json,re
import pandas as pd
import plotly.graph_objs as go


# Fungsi untuk sanitasi input
def sanitize_input(value):
    if value is None:
        return None
    return escape(re.sub(r"[;'\"]", "", str(value)))

@login_required
def splitOfficialChartPage(request):
    return render(request, 'admin-selling/official/coa-chart.html')


@login_required
def niChartPlot(request):
    typeFilter   = request.GET.get('materialFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    bulanFilter  = request.GET.get('bulanFilter')
    tahunFilter  = request.GET.get('tahunFilter')

    # --- SQL Query ---
    sql_query = """
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.ni) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS ni_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni, 0) AS ni_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(((SUM(t1.tonnage * t1.ni) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.ni) / NULLIF(t2.ni, 0) * 100, 0) AS ni_diff
        FROM details_selling_barge_split t1
        LEFT JOIN (
            SELECT 
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(ni), 0) AS ni,
                type_selling
            FROM sellings_official_view
            GROUP BY product_code, type_selling
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
    """

    filters = []
    if startDate and endDate:
        filters.append(f"t1.date_barge_out BETWEEN '{startDate}' AND '{endDate}'")
    if typeFilter:
        filters.append(f"t1.sale_adjust = '{typeFilter}'")
    if bulanFilter and tahunFilter:
        filters.append(f"EXTRACT(MONTH FROM t1.date_barge_out) = {bulanFilter} AND EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")
    elif tahunFilter:
        filters.append(f"EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")

    if filters:
        sql_query += " AND " + " AND ".join(filters)

    sql_query += """
        GROUP BY t1.date_barge_in,t1.code_lot, t1.barge_code,
                 t2.tonnage_official, t2.ni
        ORDER BY t1.date_barge_in ASC
    """

    # Ambil data ke DataFrame
    df = pd.read_sql_query(sql_query, connections['kqms_db'])

    data = df.to_dict(orient="records")
    return JsonResponse(data, safe=False)

@login_required
def feChartPlot(request):
    typeFilter   = request.GET.get('materialFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    bulanFilter  = request.GET.get('bulanFilter')
    tahunFilter  = request.GET.get('tahunFilter')

    # --- SQL Query ---
    sql_query = """
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.fe) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS fe_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.fe, 0) AS fe_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(((SUM(t1.tonnage * t1.fe) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.fe) / NULLIF(t2.fe, 0) * 100, 0) AS fe_diff
        FROM details_selling_barge_split t1
        LEFT JOIN (
            SELECT 
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(fe), 0) AS fe,
                type_selling
            FROM sellings_official_view
            GROUP BY product_code, type_selling
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
    """

    filters = []
    if startDate and endDate:
        filters.append(f"t1.date_barge_out BETWEEN '{startDate}' AND '{endDate}'")
    if typeFilter:
        filters.append(f"t1.sale_adjust = '{typeFilter}'")
    if bulanFilter and tahunFilter:
        filters.append(f"EXTRACT(MONTH FROM t1.date_barge_out) = {bulanFilter} AND EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")
    elif tahunFilter:
        filters.append(f"EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")

    if filters:
        sql_query += " AND " + " AND ".join(filters)

    sql_query += """
        GROUP BY t1.date_barge_in,t1.code_lot, t1.barge_code,
                 t2.tonnage_official, t2.fe
        ORDER BY t1.date_barge_in ASC
    """

    # Ambil data ke DataFrame
    df = pd.read_sql_query(sql_query, connections['kqms_db'])

    data = df.to_dict(orient="records")
    return JsonResponse(data, safe=False)

@login_required
def mgoChartPlot(request):
    typeFilter   = request.GET.get('materialFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    bulanFilter  = request.GET.get('bulanFilter')
    tahunFilter  = request.GET.get('tahunFilter')

    # --- SQL Query ---
    sql_query = """
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.mgo) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS mgo_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.mgo, 0) AS mgo_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(((SUM(t1.tonnage * t1.mgo) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.mgo) / NULLIF(t2.mgo, 0) * 100, 0) AS mgo_diff
        FROM details_selling_barge_split t1
        LEFT JOIN (
            SELECT 
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(mgo), 0) AS mgo,
                type_selling
            FROM sellings_official_view
            GROUP BY product_code, type_selling
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
    """

    filters = []
    if startDate and endDate:
        filters.append(f"t1.date_barge_out BETWEEN '{startDate}' AND '{endDate}'")
    if typeFilter:
        filters.append(f"t1.sale_adjust = '{typeFilter}'")
    if bulanFilter and tahunFilter:
        filters.append(f"EXTRACT(MONTH FROM t1.date_barge_out) = {bulanFilter} AND EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")
    elif tahunFilter:
        filters.append(f"EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")

    if filters:
        sql_query += " AND " + " AND ".join(filters)

    sql_query += """
        GROUP BY t1.date_barge_in,t1.code_lot, t1.barge_code,
                 t2.tonnage_official, t2.mgo
        ORDER BY t1.date_barge_in ASC
    """

    # Ambil data ke DataFrame
    df = pd.read_sql_query(sql_query, connections['kqms_db'])

    data = df.to_dict(orient="records")
    return JsonResponse(data, safe=False)

@login_required
def sio2ChartPlot(request):
    typeFilter   = request.GET.get('materialFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    bulanFilter  = request.GET.get('bulanFilter')
    tahunFilter  = request.GET.get('tahunFilter')

    # --- SQL Query ---
    sql_query = """
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS sio2_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.sio2, 0) AS sio2_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(((SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.sio2) / NULLIF(t2.sio2, 0) * 100, 0) AS sio2_diff
        FROM details_selling_barge_split t1
        LEFT JOIN (
            SELECT 
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(sio2), 0) AS sio2,
                type_selling
            FROM sellings_official_view
            GROUP BY product_code, type_selling
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
    """

    filters = []
    if startDate and endDate:
        filters.append(f"t1.date_barge_out BETWEEN '{startDate}' AND '{endDate}'")
    if typeFilter:
        filters.append(f"t1.sale_adjust = '{typeFilter}'")
    if bulanFilter and tahunFilter:
        filters.append(f"EXTRACT(MONTH FROM t1.date_barge_out) = {bulanFilter} AND EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")
    elif tahunFilter:
        filters.append(f"EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")

    if filters:
        sql_query += " AND " + " AND ".join(filters)

    sql_query += """
        GROUP BY t1.date_barge_in,t1.code_lot, t1.barge_code,
                 t2.tonnage_official, t2.sio2
        ORDER BY t1.date_barge_in ASC
    """

    # Ambil data ke DataFrame
    df = pd.read_sql_query(sql_query, connections['kqms_db'])

    data = df.to_dict(orient="records")
    return JsonResponse(data, safe=False)

@login_required
def smChartPlot(request):
    typeFilter   = request.GET.get('materialFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    bulanFilter  = request.GET.get('bulanFilter')
    tahunFilter  = request.GET.get('tahunFilter')
    theme        = request.GET.get("theme", "light")

    # --- SQL Query ---
    sql_query = """
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.sm) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS sm_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.sm, 0) AS sm_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(((SUM(t1.tonnage * t1.sm) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.sm) / NULLIF(t2.sm, 0) * 100, 0) AS sm_diff
        FROM details_selling_barge_split t1
        LEFT JOIN (
            SELECT 
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(sm), 0) AS sm,
                type_selling
            FROM sellings_official_view
            GROUP BY product_code, type_selling
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
    """

    filters = []
    if startDate and endDate:
        filters.append(f"t1.date_barge_out BETWEEN '{startDate}' AND '{endDate}'")
    if typeFilter:
        filters.append(f"t1.sale_adjust = '{typeFilter}'")
    if bulanFilter and tahunFilter:
        filters.append(f"EXTRACT(MONTH FROM t1.date_barge_out) = {bulanFilter} AND EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")
    elif tahunFilter:
        filters.append(f"EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")

    if filters:
        sql_query += " AND " + " AND ".join(filters)

    sql_query += """
        GROUP BY t1.date_barge_in,t1.code_lot, t1.barge_code,
                 t2.tonnage_official, t2.sm
        ORDER BY t1.date_barge_in ASC
    """

    # Ambil data ke DataFrame
    df = pd.read_sql_query(sql_query, connections['kqms_db'])

    data = df.to_dict(orient="records")
    return JsonResponse(data, safe=False)


