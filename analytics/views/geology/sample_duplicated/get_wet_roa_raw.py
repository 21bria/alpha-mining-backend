from datetime import datetime
from django.http import JsonResponse
from django.db import connection
import pandas as pd

ANALYTES = ["ni", "co", "fe", "mgo", "sio2"]


def safe_int(val):
    return int(val) if val is not None else 0


def safe_float(val):
    return float(val) if val is not None else 0.0


def safe_percent(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100, 2)


def build_summary(where_clause, params):
    query = f"""
        SELECT
            COUNT(CASE WHEN ni_ori IS NOT NULL THEN ni_ori END) AS jlm_ni,
            COUNT(CASE WHEN ni_error = '0' AND ni_ori IS NOT NULL THEN ni_ori END) AS error_ni,
            COUNT(CASE WHEN ni_error = '1' AND ni_ori IS NOT NULL THEN ni_ori END) AS good_ni,
            ROUND(COALESCE(AVG(CASE WHEN ni_diff IS NOT NULL THEN ni_diff END), 0), 3) AS avg_ni,

            COUNT(CASE WHEN co_ori IS NOT NULL THEN co_ori END) AS jlm_co,
            COUNT(CASE WHEN co_error = '0' AND co_ori IS NOT NULL THEN co_ori END) AS error_co,
            COUNT(CASE WHEN co_error = '1' AND co_ori IS NOT NULL THEN co_ori END) AS good_co,
            ROUND(COALESCE(AVG(CASE WHEN co_diff IS NOT NULL THEN co_diff END), 0), 3) AS avg_co,

            COUNT(CASE WHEN fe_ori IS NOT NULL THEN fe_ori END) AS jlm_fe,
            COUNT(CASE WHEN fe_error = '0' AND fe_ori IS NOT NULL THEN fe_ori END) AS error_fe,
            COUNT(CASE WHEN fe_error = '1' AND fe_ori IS NOT NULL THEN fe_ori END) AS good_fe,
            ROUND(COALESCE(AVG(CASE WHEN fe_diff IS NOT NULL THEN fe_diff END), 0), 3) AS avg_fe,

            COUNT(CASE WHEN mgo_ori IS NOT NULL THEN mgo_ori END) AS jlm_mgo,
            COUNT(CASE WHEN mgo_error = '0' AND mgo_ori IS NOT NULL THEN mgo_ori END) AS error_mgo,
            COUNT(CASE WHEN mgo_error = '1' AND mgo_ori IS NOT NULL THEN mgo_ori END) AS good_mgo,
            ROUND(COALESCE(AVG(CASE WHEN mgo_diff IS NOT NULL THEN mgo_diff END), 0), 3) AS avg_mgo,

            COUNT(CASE WHEN sio2_ori IS NOT NULL THEN sio2_ori END) AS jlm_sio2,
            COUNT(CASE WHEN sio2_error = '0' AND sio2_ori IS NOT NULL THEN sio2_ori END) AS error_sio2,
            COUNT(CASE WHEN sio2_error = '1' AND sio2_ori IS NOT NULL THEN sio2_ori END) AS good_sio2,
            ROUND(COALESCE(AVG(CASE WHEN sio2_diff IS NOT NULL THEN sio2_diff END), 0), 3) AS avg_sio2
        FROM view_sample_duplicated_roa
        {where_clause}
    """

    df = pd.read_sql_query(query, connection, params=params)

    if df.empty:
        return {
            "rows": [
                {"description": "Total Sample", "ni": 0, "co": 0, "fe": 0, "mgo": 0, "sio2": 0},
                {"description": "Accept samples", "ni": 0, "co": 0, "fe": 0, "mgo": 0, "sio2": 0},
                {"description": "Accept samples(%)", "ni": 0, "co": 0, "fe": 0, "mgo": 0, "sio2": 0},
                {"description": "Error samples", "ni": 0, "co": 0, "fe": 0, "mgo": 0, "sio2": 0},
                {"description": "Error samples(%)", "ni": 0, "co": 0, "fe": 0, "mgo": 0, "sio2": 0},
                {"description": "Average Different", "ni": 0, "co": 0, "fe": 0, "mgo": 0, "sio2": 0},
            ]
        }

    row = df.iloc[0]

    jlm_ni, error_ni, good_ni, avg_ni = safe_int(row["jlm_ni"]), safe_int(row["error_ni"]), safe_int(row["good_ni"]), safe_float(row["avg_ni"])
    jlm_co, error_co, good_co, avg_co = safe_int(row["jlm_co"]), safe_int(row["error_co"]), safe_int(row["good_co"]), safe_float(row["avg_co"])
    jlm_fe, error_fe, good_fe, avg_fe = safe_int(row["jlm_fe"]), safe_int(row["error_fe"]), safe_int(row["good_fe"]), safe_float(row["avg_fe"])
    jlm_mgo, error_mgo, good_mgo, avg_mgo = safe_int(row["jlm_mgo"]), safe_int(row["error_mgo"]), safe_int(row["good_mgo"]), safe_float(row["avg_mgo"])
    jlm_sio2, error_sio2, good_sio2, avg_sio2 = safe_int(row["jlm_sio2"]), safe_int(row["error_sio2"]), safe_int(row["good_sio2"]), safe_float(row["avg_sio2"])

    return {
        "rows": [
            {
                "description": "Total Sample",
                "ni": jlm_ni, "co": jlm_co, "fe": jlm_fe, "mgo": jlm_mgo, "sio2": jlm_sio2,
            },
            {
                "description": "Accept samples",
                "ni": good_ni, "co": good_co, "fe": good_fe, "mgo": good_mgo, "sio2": good_sio2,
            },
            {
                "description": "Accept samples(%)",
                "ni": safe_percent(good_ni, jlm_ni),
                "co": safe_percent(good_co, jlm_co),
                "fe": safe_percent(good_fe, jlm_fe),
                "mgo": safe_percent(good_mgo, jlm_mgo),
                "sio2": safe_percent(good_sio2, jlm_sio2),
            },
            {
                "description": "Error samples",
                "ni": error_ni, "co": error_co, "fe": error_fe, "mgo": error_mgo, "sio2": error_sio2,
            },
            {
                "description": "Error samples(%)",
                "ni": safe_percent(error_ni, jlm_ni),
                "co": safe_percent(error_co, jlm_co),
                "fe": safe_percent(error_fe, jlm_fe),
                "mgo": safe_percent(error_mgo, jlm_mgo),
                "sio2": safe_percent(error_sio2, jlm_sio2),
            },
            {
                "description": "Average Different",
                "ni": avg_ni, "co": avg_co, "fe": avg_fe, "mgo": avg_mgo, "sio2": avg_sio2,
            },
        ]
    }


def get_raw_wet_roa(request):
    start_date = request.GET.get("startDate") or request.GET.get("start_date")
    end_date = request.GET.get("endDate") or request.GET.get("end_date")
    iup_id = request.GET.get("iup_id") or request.GET.get("iup_filter")

    if not end_date:
        return JsonResponse({
            "year": {"title": "Table Wet duplicated by Year", "rows": []},
            "month": {"title": "Table Wet duplicated by Month", "rows": []},
            "range": {"title": "Table Wet duplicated by Range", "rows": []},
        })

    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else end_dt
    except ValueError:
        return JsonResponse({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    def build_where(base_clauses, base_params):
        clauses = list(base_clauses)
        params = list(base_params)

        if iup_id not in (None, "", "null", "undefined"):
            clauses.append("iup_id = %s")
            params.append(iup_id)

        return "WHERE " + " AND ".join(clauses), params

    year_where, year_params = build_where(
        ["EXTRACT(YEAR FROM release_date) = %s"],
        [end_dt.year],
    )

    month_where, month_params = build_where(
        [
            "EXTRACT(YEAR FROM release_date) = %s",
            "EXTRACT(MONTH FROM release_date) = %s",
        ],
        [end_dt.year, end_dt.month],
    )

    range_where, range_params = build_where(
        ["release_date BETWEEN %s AND %s"],
        [start_dt, end_dt],
    )

    year_data = build_summary(year_where, year_params)
    month_data = build_summary(month_where, month_params)
    range_data = build_summary(range_where, range_params)

    return JsonResponse({
        "year": {
            "title": f"Table Wet duplicated by Year ({end_dt.year})",
            "rows": year_data["rows"],
        },
        "month": {
            "title": f"Table Wet duplicated by Month ({end_dt.strftime('%B %Y')})",
            "rows": month_data["rows"],
        },
        "range": {
            "title": f"Table Wet duplicated by Range ({start_dt} to {end_dt})",
            "rows": range_data["rows"],
        },
    })