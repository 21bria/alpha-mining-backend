from datetime import datetime
from django.http import JsonResponse
from django.db import connection
import pandas as pd

def chart_sample_release_year(request):
    end_date = request.GET.get("end_date")
    iup_id = request.GET.get("iup_id") or request.GET.get("iup_filter")

    if not end_date:
        return JsonResponse({
            "title": "Sample Release Status by Year",
            "categories": [
                "Sas-roa", "Sas-mral",
                "Lis-roa", "Lis-mral",
                "QA-roa", "QA-mral",
                "Gc-roa", "Gc-mral",
            ],
            "order": [0, 0, 0, 0, 0, 0, 0, 0],
            "released": [0, 0, 0, 0, 0, 0, 0, 0],
            "unreleased": [0, 0, 0, 0, 0, 0, 0, 0],
        })

    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    filter_year = end_dt.year
    year_expr = "EXTRACT(YEAR FROM date_production)"

    where_clauses = [f"{year_expr} = %s"]
    params = [filter_year]

    if iup_id not in (None, "", "null", "undefined"):
        where_clauses.append("iup_id = %s")
        params.append(iup_id)

    where_clause = " AND ".join(where_clauses)

    query = f"""
        SELECT
            {year_expr} AS tahun,

            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'CKS' THEN 1 END) + 
            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc_mral_order,

            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'CKS' THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc_mral_released,

            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'CKS' THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc_mral_pre_released,

            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'CKS' THEN 1 END) + 
            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc_roa_order,

            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'CKS' THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc_roa_released,

            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'CKS' THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc_roa_pre_released,

            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa_mral_order,

            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa_mral_released,

            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa_mral_pre_released,

            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa_roa_order,

            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa_roa_released,

            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa_roa_pre_released,

            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'lis' THEN 1 END) AS lis_mral_order,
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'lis' THEN 1 END) AS lis_mral_released,
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'lis' THEN 1 END) AS lis_mral_pre_released,

            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'lis' THEN 1 END) AS lis_roa_order,
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'lis' THEN 1 END) AS lis_roa_released,
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'lis' THEN 1 END) AS lis_roa_pre_released,

            COUNT(CASE WHEN mral_order = 'Yes' AND type_sample = 'sas' THEN 1 END) AS sas_mral_order,
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NOT NULL AND type_sample = 'sas' THEN 1 END) AS sas_mral_released,
            COUNT(CASE WHEN mral_order = 'Yes' AND release_mral IS NULL AND type_sample = 'sas' THEN 1 END) AS sas_mral_pre_released,

            COUNT(CASE WHEN roa_order = 'Yes' AND type_sample = 'sas' THEN 1 END) AS sas_roa_order,
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NOT NULL AND type_sample = 'sas' THEN 1 END) AS sas_roa_released,
            COUNT(CASE WHEN roa_order = 'Yes' AND release_roa IS NULL AND type_sample = 'sas' THEN 1 END) AS sas_roa_pre_released

        FROM view_sample_type_count
        WHERE {where_clause}
        GROUP BY {year_expr}
    """

    df = pd.read_sql_query(query, connection, params=params)

    categories = [
        "Sas-roa", "Sas-mral",
        "Lis-roa", "Lis-mral",
        "QA-roa", "QA-mral",
        "Gc-roa", "Gc-mral",
    ]

    if df.empty:
        return JsonResponse({
            "title": f"Sample Release Status for {filter_year}",
            "categories": categories,
            "order": [0] * len(categories),
            "released": [0] * len(categories),
            "unreleased": [0] * len(categories),
        })

    row = df.iloc[0]

    data_order = [
        int(row["sas_roa_order"] or 0),
        int(row["sas_mral_order"] or 0),
        int(row["lis_roa_order"] or 0),
        int(row["lis_mral_order"] or 0),
        int(row["qa_roa_order"] or 0),
        int(row["qa_mral_order"] or 0),
        int(row["gc_roa_order"] or 0),
        int(row["gc_mral_order"] or 0),
    ]

    data_released = [
        int(row["sas_roa_released"] or 0),
        int(row["sas_mral_released"] or 0),
        int(row["lis_roa_released"] or 0),
        int(row["lis_mral_released"] or 0),
        int(row["qa_roa_released"] or 0),
        int(row["qa_mral_released"] or 0),
        int(row["gc_roa_released"] or 0),
        int(row["gc_mral_released"] or 0),
    ]

    data_unreleased = [
        int(row["sas_roa_pre_released"] or 0),
        int(row["sas_mral_pre_released"] or 0),
        int(row["lis_roa_pre_released"] or 0),
        int(row["lis_mral_pre_released"] or 0),
        int(row["qa_roa_pre_released"] or 0),
        int(row["qa_mral_pre_released"] or 0),
        int(row["gc_roa_pre_released"] or 0),
        int(row["gc_mral_pre_released"] or 0),
    ]

    return JsonResponse({
        "title": f"Sample Release Status for {filter_year}",
        "categories": categories,
        "order": data_order,
        "released": data_released,
        "unreleased": data_unreleased,
    })

def chart_sample_type_range(request):
    start_date = request.GET.get("start_date") or request.GET.get("startDate")
    end_date = request.GET.get("end_date") or request.GET.get("endDate")
    iup_id = request.GET.get("iup_id") or request.GET.get("iup_filter")

    if not start_date or not end_date:
        return JsonResponse({
            "gc": {"title": "Data GC", "labels": [], "series": {"spc": [], "cks": []}},
            "qa": {"title": "Data QAQC", "labels": [], "series": {"pds": [], "qaqc": [], "spc_qa": []}},
            "sale": {"title": "Data Sale", "labels": [], "series": {"sas": [], "lis": []}},
        })

    where_clauses = ["date_production BETWEEN %s AND %s"]
    params = [start_date, end_date]

    if iup_id not in (None, "", "null", "undefined"):
        where_clauses.append("iup_id = %s")
        params.append(iup_id)

    query = f"""
        SELECT
            date_production,
            COUNT(CASE WHEN type_sample = 'CKS' THEN 1 END) AS cks,
            COUNT(CASE WHEN type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS spc,

            COUNT(CASE WHEN type_sample = 'PDS' THEN 1 END) AS pds,
            COUNT(CASE WHEN type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) AS qaqc,
            COUNT(CASE WHEN type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS spc_qa,

            COUNT(CASE WHEN type_sample IN ('LIS', 'LIS_CKS') THEN 1 END) AS lis,
            COUNT(CASE WHEN type_sample IN ('SAS', 'SAS_CKS') THEN 1 END) AS sas
        FROM view_sample_type_count
        WHERE {' AND '.join(where_clauses)}
        GROUP BY date_production
        ORDER BY date_production ASC
    """

    df = pd.read_sql_query(query, connection, params=params)

    if df.empty:
        return JsonResponse({
            "gc": {
                "title": f"Data GC : {start_date} to {end_date}",
                "labels": [],
                "series": {"spc": [], "cks": []},
            },
            "qa": {
                "title": f"Data QAQC : {start_date} to {end_date}",
                "labels": [],
                "series": {"pds": [], "qaqc": [], "spc_qa": []},
            },
            "sale": {
                "title": f"Data Sale : {start_date} to {end_date}",
                "labels": [],
                "series": {"sas": [], "lis": []},
            },
        })

    labels = [str(x) for x in df["date_production"].tolist()]

    return JsonResponse({
        "gc": {
            "title": f"Data GC : {start_date} to {end_date}",
            "labels": labels,
            "series": {
                "spc": [int(x or 0) for x in df["spc"].tolist()],
                "cks": [int(x or 0) for x in df["cks"].tolist()],
            },
        },
        "qa": {
            "title": f"Data QAQC : {start_date} to {end_date}",
            "labels": labels,
            "series": {
                "pds": [int(x or 0) for x in df["pds"].tolist()],
                "qaqc": [int(x or 0) for x in df["qaqc"].tolist()],
                "spc_qa": [int(x or 0) for x in df["spc_qa"].tolist()],
            },
        },
        "sale": {
            "title": f"Data Sale : {start_date} to {end_date}",
            "labels": labels,
            "series": {
                "sas": [int(x or 0) for x in df["sas"].tolist()],
                "lis": [int(x or 0) for x in df["lis"].tolist()],
            },
        },
    })