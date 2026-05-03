from django.http import JsonResponse
from django.db import connection
from django.utils.html import escape
import json,re
import pandas as pd
from datetime import datetime, timedelta
from analytics.services.iup_filter import build_iup_clause

def parse_week_value(week_value):
    if not week_value:
        return None

    week_value = str(week_value).strip()
    # format: 2026-09 -> ambil 09
    if "-" in week_value:
        parts = week_value.split("-")
        week_value = parts[-1]

    try:
        return int(week_value)
    except (TypeError, ValueError):
        return None

def niChartCoa(request):
    iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    week        = request.GET.get("week")
    date_start  = request.GET.get("date_start")
    date_end    = request.GET.get("date_end")
    filter_date = request.GET.get("filter_date")
    typeFilter  = request.GET.get("materialFilter")

    # IUP filter clause
    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")
    t2_iup_clause, t2_iup_params = build_iup_clause(iup_filter, "view_selling_official")

    base_query = f"""
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(
                SUM(t1.tonnage * t1.ni) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS ni_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni, 0) AS ni_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.ni) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.ni
                ) / NULLIF(t2.ni, 0) * 100,
                0
            ) AS ni_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT
                product_code,
                tonnage AS tonnage_official,
                ni,
                type_selling,
                re_assay
            FROM (
                SELECT
                    id,
                    product_code,
                    tonnage,
                    ni,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
                WHERE 1=1
                {t2_iup_clause}
            ) x
            WHERE x.rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t2_iup_params)
    params.extend(t1_iup_params)

    filters = []

    # Daily
    if filter_type == "daily" and filter_date:
        filters.append("DATE(t1.date_barge_out) = %s")
        params.append(filter_date)

    # Range
    elif filter_type == "range" and date_start and date_end:
        filters.append("t1.date_barge_out BETWEEN %s AND %s")
        params.extend([date_start, date_end])

    # Weekly
    elif filter_type == "weekly" and year and month and week:
        try:
            year_int = int(year)
            month_int = int(month)
            week_int = parse_week_value(week)

            if not week_int:
                return JsonResponse({"error": "Invalid week format"}, status=400)

            first_day = datetime(year_int, month_int, 1)
            start_date = first_day + timedelta(days=(week_int - 1) * 7)
            end_date = start_date + timedelta(days=6)

            # koreksi agar tidak lewat akhir bulan
            if end_date.month != month_int:
                if month_int == 12:
                    next_month = datetime(year_int + 1, 1, 1)
                else:
                    next_month = datetime(year_int, month_int + 1, 1)
                end_date = next_month - timedelta(days=1)

            filters.append("t1.date_barge_out BETWEEN %s AND %s")
            params.extend([start_date.date(), end_date.date()])

        except ValueError:
            return JsonResponse({"error": "Invalid weekly parameters"}, status=400)

    # Monthly
    elif filter_type == "monthly" and year and month:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            filters.append("EXTRACT(MONTH FROM t1.date_barge_out) = %s")
            params.extend([int(year), int(month)])
        except ValueError:
            return JsonResponse({"error": "Invalid monthly parameters"}, status=400)

    # Yearly
    elif filter_type == "yearly" and year:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            params.append(int(year))
        except ValueError:
            return JsonResponse({"error": "Invalid yearly parameters"}, status=400)

    # All
    elif filter_type == "all":
        pass

    else:
        return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

    # Filter tambahan material
    if typeFilter:
        filters.append("t1.sale_adjust = %s")
        params.append(typeFilter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += """
        GROUP BY 
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.ni
        ORDER BY t1.date_barge_in ASC
    """

    df = pd.read_sql_query(base_query, connection, params=params)
    details = df.to_dict(orient="records")

    compare = {
        "x_data": [row["lot_barge"] for row in details],
        "y_split": [round(row["ni_split"] or 0, 2) for row in details],
        "y_official": [round(row["ni_official"] or 0, 2) for row in details],
        "tonnage_split": [round(row["tonnage_split"] or 0, 2) for row in details],
        "tonnage_official": [round(row["tonnage_official"] or 0, 2) for row in details],
        "ni_diff": [round(row["ni_diff"] or 0, 3) for row in details],
        "tonnage_diff": [round(row["tonnage_diff"] or 0, 2) for row in details],
    }

    return JsonResponse({
        "compare": compare,
        "details": details
    }, safe=False)

def feChartCoa(request):
    iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    week        = request.GET.get("week")
    date_start  = request.GET.get("date_start")
    date_end    = request.GET.get("date_end")
    filter_date = request.GET.get("filter_date")
    typeFilter  = request.GET.get("materialFilter")

    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")
    t2_iup_clause, t2_iup_params = build_iup_clause(iup_filter, "view_selling_official")

    base_query = f"""
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(
                SUM(t1.tonnage * t1.fe) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS fe_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.fe, 0) AS fe_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.fe) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.fe
                ) / NULLIF(t2.fe, 0) * 100,
                0
            ) AS fe_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT
                product_code,
                tonnage AS tonnage_official,
                fe,
                type_selling,
                re_assay
            FROM (
                SELECT
                    id,
                    product_code,
                    tonnage,
                    fe,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
                WHERE 1=1
                {t2_iup_clause}
            ) x
            WHERE x.rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t2_iup_params)
    params.extend(t1_iup_params)

    filters = []

    if filter_type == "daily" and filter_date:
        filters.append("DATE(t1.date_barge_out) = %s")
        params.append(filter_date)

    elif filter_type == "range" and date_start and date_end:
        filters.append("t1.date_barge_out BETWEEN %s AND %s")
        params.extend([date_start, date_end])

    elif filter_type == "weekly" and year and month and week:
        try:
            year_int = int(year)
            month_int = int(month)
            week_int = parse_week_value(week)

            if not week_int:
                return JsonResponse({"error": "Invalid week format"}, status=400)

            first_day = datetime(year_int, month_int, 1)
            start_date = first_day + timedelta(days=(week_int - 1) * 7)
            end_date = start_date + timedelta(days=6)

            if end_date.month != month_int:
                if month_int == 12:
                    next_month = datetime(year_int + 1, 1, 1)
                else:
                    next_month = datetime(year_int, month_int + 1, 1)
                end_date = next_month - timedelta(days=1)

            filters.append("t1.date_barge_out BETWEEN %s AND %s")
            params.extend([start_date.date(), end_date.date()])

        except ValueError:
            return JsonResponse({"error": "Invalid weekly parameters"}, status=400)

    elif filter_type == "monthly" and year and month:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            filters.append("EXTRACT(MONTH FROM t1.date_barge_out) = %s")
            params.extend([int(year), int(month)])
        except ValueError:
            return JsonResponse({"error": "Invalid monthly parameters"}, status=400)

    elif filter_type == "yearly" and year:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            params.append(int(year))
        except ValueError:
            return JsonResponse({"error": "Invalid yearly parameters"}, status=400)

    elif filter_type == "all":
        pass

    else:
        return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

    if typeFilter:
        filters.append("t1.sale_adjust = %s")
        params.append(typeFilter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += """
        GROUP BY 
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.fe
        ORDER BY t1.date_barge_in ASC
    """

    df = pd.read_sql_query(base_query, connection, params=params)
    details = df.to_dict(orient="records")

    compare = {
        "x_data": [row["lot_barge"] for row in details],
        "y_split": [round(row["fe_split"] or 0, 2) for row in details],
        "y_official": [round(row["fe_official"] or 0, 2) for row in details],
        "tonnage_split": [round(row["tonnage_split"] or 0, 2) for row in details],
        "tonnage_official": [round(row["tonnage_official"] or 0, 2) for row in details],
        "fe_diff": [round(row["fe_diff"] or 0, 3) for row in details],
        "tonnage_diff": [round(row["tonnage_diff"] or 0, 2) for row in details],
    }

    return JsonResponse({
        "compare": compare,
        "details": details
    }, safe=False)

def mgoChartCoa(request):
    iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    week        = request.GET.get("week")
    date_start  = request.GET.get("date_start")
    date_end    = request.GET.get("date_end")
    filter_date = request.GET.get("filter_date")
    typeFilter  = request.GET.get("materialFilter")

    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")
    t2_iup_clause, t2_iup_params = build_iup_clause(iup_filter, "view_selling_official")

    base_query = f"""
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(
                SUM(t1.tonnage * t1.mgo) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS mgo_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.mgo, 0) AS mgo_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.mgo) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.mgo
                ) / NULLIF(t2.mgo, 0) * 100,
                0
            ) AS mgo_diff
        FROM view_selling_split_barge t1
         LEFT JOIN (
            SELECT
                product_code,
                tonnage AS tonnage_official,
                mgo,
                type_selling,
                re_assay
            FROM (
                SELECT
                    id,
                    product_code,
                    tonnage,
                    mgo,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
                WHERE 1=1
                {t2_iup_clause}
            ) x
            WHERE x.rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t2_iup_params)
    params.extend(t1_iup_params)

    filters = []

    if filter_type == "daily" and filter_date:
        filters.append("DATE(t1.date_barge_out) = %s")
        params.append(filter_date)

    elif filter_type == "range" and date_start and date_end:
        filters.append("t1.date_barge_out BETWEEN %s AND %s")
        params.extend([date_start, date_end])

    elif filter_type == "weekly" and year and month and week:
        try:
            year_int = int(year)
            month_int = int(month)
            week_int = parse_week_value(week)

            if not week_int:
                return JsonResponse({"error": "Invalid week format"}, status=400)

            first_day = datetime(year_int, month_int, 1)
            start_date = first_day + timedelta(days=(week_int - 1) * 7)
            end_date = start_date + timedelta(days=6)

            if end_date.month != month_int:
                if month_int == 12:
                    next_month = datetime(year_int + 1, 1, 1)
                else:
                    next_month = datetime(year_int, month_int + 1, 1)
                end_date = next_month - timedelta(days=1)

            filters.append("t1.date_barge_out BETWEEN %s AND %s")
            params.extend([start_date.date(), end_date.date()])

        except ValueError:
            return JsonResponse({"error": "Invalid weekly parameters"}, status=400)

    elif filter_type == "monthly" and year and month:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            filters.append("EXTRACT(MONTH FROM t1.date_barge_out) = %s")
            params.extend([int(year), int(month)])
        except ValueError:
            return JsonResponse({"error": "Invalid monthly parameters"}, status=400)

    elif filter_type == "yearly" and year:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            params.append(int(year))
        except ValueError:
            return JsonResponse({"error": "Invalid yearly parameters"}, status=400)

    elif filter_type == "all":
        pass

    else:
        return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

    if typeFilter:
        filters.append("t1.sale_adjust = %s")
        params.append(typeFilter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += """
        GROUP BY 
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.mgo
        ORDER BY t1.date_barge_in ASC
    """

    df = pd.read_sql_query(base_query, connection, params=params)
    details = df.to_dict(orient="records")

    compare = {
        "x_data": [row["lot_barge"] for row in details],
        "y_split": [round(row["mgo_split"] or 0, 2) for row in details],
        "y_official": [round(row["mgo_official"] or 0, 2) for row in details],
        "tonnage_split": [round(row["tonnage_split"] or 0, 2) for row in details],
        "tonnage_official": [round(row["tonnage_official"] or 0, 2) for row in details],
        "mgo_diff": [round(row["mgo_diff"] or 0, 3) for row in details],
        "tonnage_diff": [round(row["tonnage_diff"] or 0, 2) for row in details],
    }

    return JsonResponse({
        "compare": compare,
        "details": details
    }, safe=False)

def sio2ChartCoa(request):
    iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    week        = request.GET.get("week")
    date_start  = request.GET.get("date_start")
    date_end    = request.GET.get("date_end")
    filter_date = request.GET.get("filter_date")
    typeFilter  = request.GET.get("materialFilter")

    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")
    t2_iup_clause, t2_iup_params = build_iup_clause(iup_filter, "view_selling_official")

    base_query = f"""
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(
                SUM(t1.tonnage * t1.sio2) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS sio2_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.sio2, 0) AS sio2_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.sio2) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.sio2
                ) / NULLIF(t2.sio2, 0) * 100,
                0
            ) AS sio2_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT
                product_code,
                tonnage AS tonnage_official,
                sio2,
                type_selling,
                re_assay
            FROM (
                SELECT
                    id,
                    product_code,
                    tonnage,
                    sio2,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
                WHERE 1=1
                {t2_iup_clause}
            ) x
            WHERE x.rn = 1
        ) AS t2 ON t1.code_lot = t2.product_codee
        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t2_iup_params)
    params.extend(t1_iup_params)

    filters = []

    if filter_type == "daily" and filter_date:
        filters.append("DATE(t1.date_barge_out) = %s")
        params.append(filter_date)

    elif filter_type == "range" and date_start and date_end:
        filters.append("t1.date_barge_out BETWEEN %s AND %s")
        params.extend([date_start, date_end])

    elif filter_type == "weekly" and year and month and week:
        try:
            year_int = int(year)
            month_int = int(month)
            week_int = parse_week_value(week)

            if not week_int:
                return JsonResponse({"error": "Invalid week format"}, status=400)

            first_day = datetime(year_int, month_int, 1)
            start_date = first_day + timedelta(days=(week_int - 1) * 7)
            end_date = start_date + timedelta(days=6)

            if end_date.month != month_int:
                if month_int == 12:
                    next_month = datetime(year_int + 1, 1, 1)
                else:
                    next_month = datetime(year_int, month_int + 1, 1)
                end_date = next_month - timedelta(days=1)

            filters.append("t1.date_barge_out BETWEEN %s AND %s")
            params.extend([start_date.date(), end_date.date()])

        except ValueError:
            return JsonResponse({"error": "Invalid weekly parameters"}, status=400)

    elif filter_type == "monthly" and year and month:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            filters.append("EXTRACT(MONTH FROM t1.date_barge_out) = %s")
            params.extend([int(year), int(month)])
        except ValueError:
            return JsonResponse({"error": "Invalid monthly parameters"}, status=400)

    elif filter_type == "yearly" and year:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            params.append(int(year))
        except ValueError:
            return JsonResponse({"error": "Invalid yearly parameters"}, status=400)

    elif filter_type == "all":
        pass

    else:
        return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

    if typeFilter:
        filters.append("t1.sale_adjust = %s")
        params.append(typeFilter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += """
        GROUP BY 
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.sio2
        ORDER BY t1.date_barge_in ASC
    """

    df = pd.read_sql_query(base_query, connection, params=params)
    details = df.to_dict(orient="records")

    compare = {
        "x_data": [row["lot_barge"] for row in details],
        "y_split": [round(row["sio2_split"] or 0, 2) for row in details],
        "y_official": [round(row["sio2_official"] or 0, 2) for row in details],
        "tonnage_split": [round(row["tonnage_split"] or 0, 2) for row in details],
        "tonnage_official": [round(row["tonnage_official"] or 0, 2) for row in details],
        "sio2_diff": [round(row["sio2_diff"] or 0, 3) for row in details],
        "tonnage_diff": [round(row["tonnage_diff"] or 0, 2) for row in details],
    }

    return JsonResponse({
        "compare": compare,
        "details": details
    }, safe=False)

def smChartCoa(request):
    iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    week        = request.GET.get("week")
    date_start  = request.GET.get("date_start")
    date_end    = request.GET.get("date_end")
    filter_date = request.GET.get("filter_date")
    typeFilter  = request.GET.get("materialFilter")

    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")
    t2_iup_clause, t2_iup_params = build_iup_clause(iup_filter, "view_selling_official")

    base_query = f"""
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(
                SUM(t1.tonnage * t1.sm) /
                NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END), 0),
                0
            ) AS sm_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.sm, 0) AS sm_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(
                (
                    (
                        SUM(t1.tonnage * t1.sm) /
                        NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)
                    ) - t2.sm
                ) / NULLIF(t2.sm, 0) * 100,
                0
            ) AS sm_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT
                product_code,
                tonnage AS tonnage_official,
                sm,
                type_selling,
                re_assay
            FROM (
                SELECT
                    id,
                    product_code,
                    tonnage,
                    sm,
                    type_selling,
                    re_assay,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_code, type_selling
                        ORDER BY COALESCE(re_assay, 0) DESC, id DESC
                    ) AS rn
                FROM view_selling_official
                WHERE 1=1
                {t2_iup_clause}
            ) x
            WHERE x.rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t2_iup_params)
    params.extend(t1_iup_params)

    filters = []

    if filter_type == "daily" and filter_date:
        filters.append("DATE(t1.date_barge_out) = %s")
        params.append(filter_date)

    elif filter_type == "range" and date_start and date_end:
        filters.append("t1.date_barge_out BETWEEN %s AND %s")
        params.extend([date_start, date_end])

    elif filter_type == "weekly" and year and month and week:
        try:
            year_int = int(year)
            month_int = int(month)
            week_int = parse_week_value(week)

            if not week_int:
                return JsonResponse({"error": "Invalid week format"}, status=400)

            first_day = datetime(year_int, month_int, 1)
            start_date = first_day + timedelta(days=(week_int - 1) * 7)
            end_date = start_date + timedelta(days=6)

            if end_date.month != month_int:
                if month_int == 12:
                    next_month = datetime(year_int + 1, 1, 1)
                else:
                    next_month = datetime(year_int, month_int + 1, 1)
                end_date = next_month - timedelta(days=1)

            filters.append("t1.date_barge_out BETWEEN %s AND %s")
            params.extend([start_date.date(), end_date.date()])

        except ValueError:
            return JsonResponse({"error": "Invalid weekly parameters"}, status=400)

    elif filter_type == "monthly" and year and month:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            filters.append("EXTRACT(MONTH FROM t1.date_barge_out) = %s")
            params.extend([int(year), int(month)])
        except ValueError:
            return JsonResponse({"error": "Invalid monthly parameters"}, status=400)

    elif filter_type == "yearly" and year:
        try:
            filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
            params.append(int(year))
        except ValueError:
            return JsonResponse({"error": "Invalid yearly parameters"}, status=400)

    elif filter_type == "all":
        pass

    else:
        return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

    if typeFilter:
        filters.append("t1.sale_adjust = %s")
        params.append(typeFilter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += """
        GROUP BY 
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.sm
        ORDER BY t1.date_barge_in ASC
    """

    df = pd.read_sql_query(base_query, connection, params=params)
    details = df.to_dict(orient="records")

    compare = {
        "x_data": [row["lot_barge"] for row in details],
        "y_split": [round(row["sm_split"] or 0, 2) for row in details],
        "y_official": [round(row["sm_official"] or 0, 2) for row in details],
        "tonnage_split": [round(row["tonnage_split"] or 0, 2) for row in details],
        "tonnage_official": [round(row["tonnage_official"] or 0, 2) for row in details],
        "sm_diff": [round(row["sm_diff"] or 0, 3) for row in details],
        "tonnage_diff": [round(row["tonnage_diff"] or 0, 2) for row in details],
    }

    return JsonResponse({
        "compare": compare,
        "details": details
    }, safe=False)

def allChartCoa(request):
    iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type = request.GET.get("filter_type")
    year        = request.GET.get("year")
    month       = request.GET.get("month")
    typeFilter  = request.GET.get("materialFilter")

    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")
    t2_iup_clause, t2_iup_params = build_iup_clause(iup_filter, "view_selling_official")

    base_query = f"""
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_code) AS barge_code,
            CONCAT(TRIM(t1.barge_code), '/', RIGHT(TRIM(t1.code_lot), 3)) AS lot_barge,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,
            COALESCE(SUM(t1.tonnage * t1.ni)   / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni   IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS ni_split,
            COALESCE(SUM(t1.tonnage * t1.fe)   / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe   IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS fe_split,
            COALESCE(SUM(t1.tonnage * t1.mgo)  / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo  IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS mgo_split,
            COALESCE(SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS sio2_split,
            COALESCE(SUM(t1.tonnage * t1.sm)   / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm   IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS sm_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni, 0)   AS ni_official,
            COALESCE(t2.fe, 0)   AS fe_official,
            COALESCE(t2.mgo, 0)  AS mgo_official,
            COALESCE(t2.sio2, 0) AS sio2_official,
            COALESCE(t2.sm, 0)   AS sm_official,
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            COALESCE(((SUM(t1.tonnage * t1.ni)   / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni   IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.ni)   / NULLIF(t2.ni, 0)   * 100, 0) AS ni_diff,
            COALESCE(((SUM(t1.tonnage * t1.fe)   / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe   IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.fe)   / NULLIF(t2.fe, 0)   * 100, 0) AS fe_diff,
            COALESCE(((SUM(t1.tonnage * t1.mgo)  / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo  IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.mgo)  / NULLIF(t2.mgo, 0)  * 100, 0) AS mgo_diff,
            COALESCE(((SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.sio2) / NULLIF(t2.sio2, 0) * 100, 0) AS sio2_diff,
            COALESCE(((SUM(t1.tonnage * t1.sm)   / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sm   IS NOT NULL THEN t1.tonnage ELSE 0 END), 0)) - t2.sm)   / NULLIF(t2.sm, 0)   * 100, 0) AS sm_diff
        FROM view_selling_split_barge t1
        LEFT JOIN (
            SELECT
                product_code,
                tonnage AS tonnage_official,
                ni,
                fe,
                mgo,
                sio2,
                sm,
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
                WHERE 1=1
                {t2_iup_clause}
            ) x
            WHERE x.rn = 1
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
        {t1_iup_clause}
    """

    params = []
    params.extend(t2_iup_params)
    params.extend(t1_iup_params)

    filters = []

    if filter_type == "monthly" and year and month:
        filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
        filters.append("EXTRACT(MONTH FROM t1.date_barge_out) = %s")
        params.extend([int(year), int(month)])

    elif filter_type == "yearly" and year:
        filters.append("EXTRACT(YEAR FROM t1.date_barge_out) = %s")
        params.append(int(year))

    elif filter_type == "all":
        pass

    else:
        return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

    if typeFilter:
        filters.append("t1.sale_adjust = %s")
        params.append(typeFilter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += """
        GROUP BY 
            t1.date_barge_in,
            t1.code_lot,
            t1.barge_code,
            t2.tonnage_official,
            t2.ni, t2.fe, t2.mgo, t2.sio2, t2.sm
        ORDER BY t1.date_barge_in ASC
    """

    df = pd.read_sql_query(base_query, connection, params=params)
    details = df.to_dict(orient="records")

    compare = {
        "x_data": [row["lot_barge"] for row in details],
        "y_data": [row["barge_code"] for row in details],

        "y_split_ni":      [round(row["ni_split"] or 0, 2) for row in details],
        "y_official_ni":   [round(row["ni_official"] or 0, 2) for row in details],

        "y_split_fe":      [round(row["fe_split"] or 0, 2) for row in details],
        "y_official_fe":   [round(row["fe_official"] or 0, 2) for row in details],

        "y_split_mgo":     [round(row["mgo_split"] or 0, 2) for row in details],
        "y_official_mgo":  [round(row["mgo_official"] or 0, 2) for row in details],

        "y_split_sio2":    [round(row["sio2_split"] or 0, 2) for row in details],
        "y_official_sio2": [round(row["sio2_official"] or 0, 2) for row in details],

        "y_split_sm":      [round(row["sm_split"] or 0, 2) for row in details],
        "y_official_sm":   [round(row["sm_official"] or 0, 2) for row in details],

        "tonnage_split":    [round(row["tonnage_split"] or 0, 2) for row in details],
        "tonnage_official": [round(row["tonnage_official"] or 0, 2) for row in details],
        "tonnage_diff":     [round(row["tonnage_diff"] or 0, 2) for row in details],

        "ni_diff":   [round(row["ni_diff"] or 0, 3) for row in details],
        "fe_diff":   [round(row["fe_diff"] or 0, 3) for row in details],
        "mgo_diff":  [round(row["mgo_diff"] or 0, 3) for row in details],
        "sio2_diff": [round(row["sio2_diff"] or 0, 3) for row in details],
        "sm_diff":   [round(row["sm_diff"] or 0, 3) for row in details],
    }

    return JsonResponse({
        "compare": compare,
        "details": details
    }, safe=False)
