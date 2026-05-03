from django.http import JsonResponse
from django.db import connection
from scipy.stats import linregress

ALLOWED_ANALYTES = ("ni", "co", "fe", "mgo", "sio2")


def empty_section(analyte: str):
    return {
        "points": [],
        "lines": {
            "axis_max": 1,
            "upper": {"x": [], "y": []},
            "center": {"x": [], "y": []},
            "lower": {"x": [], "y": []},
        },
        "stats": {
            "analyte": analyte,
            "count": 0,
            "r_squared": 0,
            "slope": 0,
            "intercept": 0,
        },
    }


def build_section(rows, analyte: str):
    points = []
    x_vals = []
    y_vals = []

    for row in rows:
        (
            release_date,
            material,
            sample_number,
            sample_original,
            iup_id_val,
            iup_code,
            iup_name,
            dup_val,
            ori_val,
        ) = row

        if dup_val is None or ori_val is None:
            continue

        x = float(dup_val)
        y = float(ori_val)

        x_vals.append(x)
        y_vals.append(y)

        points.append({
            "x": x,
            "y": y,
            "release_date": str(release_date) if release_date else None,
            "material": material,
            "sample_number": sample_number,
            "sample_original": sample_original,
            "iup_id": iup_id_val,
            "iup_code": iup_code,
            "iup_name": iup_name,
        })

    if not points:
        return empty_section(analyte)

    max_val = max(max(x_vals), max(y_vals))
    axis_max = round(max_val * 1.1, 3) if max_val > 0 else 1

    # aman kalau titik terlalu sedikit / nilai sama semua
    if len(x_vals) >= 2 and len(set(x_vals)) > 1 and len(set(y_vals)) > 1:
        slope, intercept, r_value, p_value, std_err = linregress(x_vals, y_vals)
        r_squared = float(r_value) ** 2
        slope = round(float(slope), 4)
        intercept = round(float(intercept), 4)
        r_squared = round(r_squared, 4)
    else:
        slope = 0
        intercept = 0
        r_squared = 0

    return {
        "points": points,
        "lines": {
            "axis_max": axis_max,
            "upper": {
                "x": [0, axis_max],
                "y": [0, round(axis_max * 1.1, 3)],
            },
            "center": {
                "x": [0, axis_max],
                "y": [0, axis_max],
            },
            "lower": {
                "x": [0, axis_max],
                "y": [0, round(axis_max * 0.9, 3)],
            },
        },
        "stats": {
            "analyte": analyte,
            "count": len(points),
            "r_squared": r_squared,
            "slope": slope,
            "intercept": intercept,
        },
    }


def scatter_sample_duplicate_mral(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    iup_id = request.GET.get("iup_id") or request.GET.get("iup_filter")

    if not start_date or not end_date:
        return JsonResponse({
            "ni": empty_section("ni"),
            "co": empty_section("co"),
            "fe": empty_section("fe"),
            "mgo": empty_section("mgo"),
            "sio2": empty_section("sio2"),
        })

    response_data = {}

    for analyte in ALLOWED_ANALYTES:
        ori_col = f"{analyte}_ori"

        where_clauses = [
            f"{analyte} IS NOT NULL",
            f"{ori_col} IS NOT NULL",
            "release_date BETWEEN %s AND %s",
        ]
        params = [start_date, end_date]

        if iup_id not in (None, "", "null", "undefined"):
            where_clauses.append("iup_id = %s")
            params.append(iup_id)

        query = f"""
            SELECT
                release_date,
                material,
                sample_number,
                sample_original,
                iup_id,
                iup_code,
                iup_name,
                {analyte} AS duplicated_value,
                {ori_col} AS original_value
            FROM view_sample_duplicated_mral
            WHERE {' AND '.join(where_clauses)}
            LIMIT 3000
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        response_data[analyte] = build_section(rows, analyte)

    return JsonResponse(response_data)