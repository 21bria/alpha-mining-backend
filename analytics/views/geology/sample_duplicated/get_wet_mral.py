from datetime import datetime
from django.http import JsonResponse
from django.db import connection

ANALYTES = [
    ("ni", "Ni"),
    ("co", "Co"),
    ("fe", "Fe"),
    ("mgo", "MgO"),
    ("sio2", "SiO2"),
]


def _empty_summary(title: str):
    return {
        "title": title,
        "categories": [label for _, label in ANALYTES],
        "acceptable": [0] * len(ANALYTES),
        "error": [0] * len(ANALYTES),
    }


def _build_summary(where_sql: str, params: list, title: str):
    select_parts = []
    for key, _label in ANALYTES:
        select_parts.extend([
            f"COUNT(CASE WHEN {key}_error = '1' AND {key}_ori IS NOT NULL THEN 1 END) AS good_{key}",
            f"COUNT(CASE WHEN {key}_error = '0' AND {key}_ori IS NOT NULL THEN 1 END) AS error_{key}",
        ])

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM view_sample_duplicated_mral
        {where_sql}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()

    if not row:
        return _empty_summary(title)

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))

    return {
        "title": title,
        "categories": [label for _, label in ANALYTES],
        "acceptable": [int(data.get(f"good_{key}") or 0) for key, _ in ANALYTES],
        "error": [int(data.get(f"error_{key}") or 0) for key, _ in ANALYTES],
    }


def chart_wet_mral(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    iup_id = request.GET.get("iup_id") or request.GET.get("iup_filter")

    if not end_date:
        return JsonResponse({
            "year": _empty_summary("Duplicate Summary - Year"),
            "month": _empty_summary("Duplicate Summary - Month"),
            "range": _empty_summary("Duplicate Summary - Range"),
        })

    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_dt = (
            datetime.strptime(start_date, "%Y-%m-%d").date()
            if start_date else end_dt
        )
    except ValueError:
        return JsonResponse({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    year = end_dt.year
    month = end_dt.month

    def build_where(base_clauses, extra_params):
        clauses = list(base_clauses)
        params = list(extra_params)

        if iup_id not in (None, "", "null", "undefined"):
            clauses.append("iup_id = %s")
            params.append(iup_id)

        return "WHERE " + " AND ".join(clauses), params

    # YEAR
    year_where, year_params = build_where(
        ["EXTRACT(YEAR FROM release_date) = %s"],
        [year],
    )

    # MONTH
    month_where, month_params = build_where(
        [
            "EXTRACT(YEAR FROM release_date) = %s",
            "EXTRACT(MONTH FROM release_date) = %s",
        ],
        [year, month],
    )

    # RANGE
    range_where, range_params = build_where(
        ["release_date BETWEEN %s AND %s"],
        [start_dt, end_dt],
    )

    year_data = _build_summary(
        year_where,
        year_params,
        f"Duplicate Summary - Year {year}",
    )

    month_data = _build_summary(
        month_where,
        month_params,
        f"Duplicate Summary - {end_dt.strftime('%B %Y')}",
    )

    range_data = _build_summary(
        range_where,
        range_params,
        f"Duplicate Summary - {start_dt} to {end_dt}",
    )

    return JsonResponse({
        "year": year_data,
        "month": month_data,
        "range": range_data,
    })