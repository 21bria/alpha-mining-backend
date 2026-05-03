from datetime import datetime
from django.http import JsonResponse
from django.db import connection
import pandas as pd


def _empty_sample_section(title: str):
    return {
        "title": title,
        "categories": ["SAS", "LIS", "QA", "GC"],
        "values": [0, 0, 0, 0],
    }


def _build_sample_summary(where_clause: str, params: list, title: str):
    query = f"""
        SELECT
            COUNT(CASE WHEN type_sample = 'CKS' AND sample_method IN ('BS', 'CS', 'FS', 'GRB', 'TP', 'BS_DT', 'BS_ADT') THEN 1 END) +
            COUNT(CASE WHEN type_sample = 'SPC' AND sample_method = 'SPC_GC' THEN 1 END) AS gc,

            COUNT(CASE WHEN type_sample = 'PDS' THEN 1 END) +
            COUNT(CASE WHEN type_sample = 'QAQC' AND sample_method IN ('CRM', 'DUP_PDS') THEN 1 END) +
            COUNT(CASE WHEN type_sample = 'SPC' AND sample_method = 'SPC_QA' THEN 1 END) AS qa,

            COUNT(CASE WHEN type_sample = 'LIS' THEN 1 END) AS lis,
            COUNT(CASE WHEN type_sample = 'SAS' THEN 1 END) AS sas
        FROM view_sample_type_count
        {where_clause}
    """

    df = pd.read_sql_query(query, connection, params=params)

    if df.empty:
        return _empty_sample_section(title)

    row = df.iloc[0]

    gc = int(row["gc"] or 0)
    qa = int(row["qa"] or 0)
    lis = int(row["lis"] or 0)
    sas = int(row["sas"] or 0)

    return {
        "title": title,
        "categories": ["SAS", "LIS", "QA", "GC"],
        "values": [sas, lis, qa, gc],
    }


def chart_type_count(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    iup_id = request.GET.get("iup_id") or request.GET.get("iup_filter")

    if not end_date:
        return JsonResponse({
            "year": _empty_sample_section("Sample Production - Year"),
            "month": _empty_sample_section("Sample Production - Month"),
            "week": _empty_sample_section("Sample Production - Week"),
            "range": _empty_sample_section("Sample Production - Range"),
        })

    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else end_dt
    except ValueError:
        return JsonResponse({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    # ISO week
    iso_year, iso_week, _ = end_dt.isocalendar()

    def build_where(base_clauses, base_params):
        clauses = list(base_clauses)
        params = list(base_params)

        if iup_id not in (None, "", "null", "undefined"):
            clauses.append("iup_id = %s")
            params.append(iup_id)

        return "WHERE " + " AND ".join(clauses), params

    # YEAR
    year_where, year_params = build_where(
        ["EXTRACT(YEAR FROM date_production) = %s"],
        [end_dt.year],
    )

    # MONTH
    month_where, month_params = build_where(
        [
            "EXTRACT(YEAR FROM date_production) = %s",
            "EXTRACT(MONTH FROM date_production) = %s",
        ],
        [end_dt.year, end_dt.month],
    )

    # WEEK (ISO week)
    week_where, week_params = build_where(
        [
            "EXTRACT(ISOYEAR FROM date_production) = %s",
            "EXTRACT(WEEK FROM date_production) = %s",
        ],
        [iso_year, iso_week],
    )

    # RANGE
    range_where, range_params = build_where(
        ["date_production BETWEEN %s AND %s"],
        [start_dt, end_dt],
    )

    year_data = _build_sample_summary(
        year_where,
        year_params,
        f"Sample Production for {end_dt.year}",
    )

    month_data = _build_sample_summary(
        month_where,
        month_params,
        f"Sample Production for {end_dt.strftime('%B %Y')}",
    )

    week_data = _build_sample_summary(
        week_where,
        week_params,
        f"Sample Production for Week {iso_week} ({iso_year})",
    )

    range_data = _build_sample_summary(
        range_where,
        range_params,
        f"Sample Production for Range ({start_dt} to {end_dt})",
    )

    return JsonResponse({
        "year": year_data,
        "month": month_data,
        "week": week_data,
        "range": range_data,
    })