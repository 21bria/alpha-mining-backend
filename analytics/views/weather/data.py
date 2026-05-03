# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
from datetime import datetime, date, timedelta
from django.db.utils import DatabaseError
import calendar
logger = logging.getLogger(__name__) 
from analytics.services.iup_filter import build_iup_clause
def parse_iso_week(week_value: str):
    year_str, week_str = str(week_value).split("-")
    return int(year_str), int(week_str)

def get_data_weather(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        filter_sql = "WHERE 1=1"
        params = []

        # FILTER IUP
        iup_clause, iup_params = build_iup_clause(iup_filter, "w")
        filter_sql += iup_clause
        params += iup_params

        # FILTER DATE
        if filter_type == "daily" and filter_date:
            filter_sql += " AND w.date = %s"
            params += [filter_date]

        elif filter_type == "range" and date_start and date_end:
            filter_sql += " AND w.date BETWEEN %s AND %s"
            params += [date_start, date_end]

        elif filter_type == "weekly" and year and month and week:
            try:
                # ISO week: contoh 2026-14
                if "-" in str(week):
                    year_str, week_str = str(week).split("-")
                    year = int(year_str)
                    week = int(week_str)

                    start_date = datetime.strptime(f"{year}-W{week:02}-1", "%G-W%V-%u")
                    end_date = start_date + timedelta(days=6)

                else:
                    year = int(year)
                    month = int(month)
                    week = int(week)

                    if not (1 <= month <= 12):
                        return JsonResponse({"error": "Bulan tidak valid (1–12)"}, status=400)
                    if not (1 <= week <= 5):
                        return JsonResponse({"error": "Minggu tidak valid (1–5)"}, status=400)

                    first_day = datetime(year, month, 1)
                    start_date = first_day + timedelta(days=(week - 1) * 7)
                    end_date = start_date + timedelta(days=6)

                    if end_date.month != month:
                        next_month = datetime(year, month, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

            except Exception as e:
                return JsonResponse(
                    {"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"},
                    status=400
                )

            filter_sql += " AND w.date BETWEEN %s AND %s"
            params += [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

        elif filter_type == "monthly" and year and month:
            filter_sql += " AND EXTRACT(YEAR FROM w.date) = %s AND EXTRACT(MONTH FROM w.date) = %s"
            params += [year, month]

        elif filter_type == "yearly" and year:
            filter_sql += " AND EXTRACT(YEAR FROM w.date) = %s"
            params += [year]

        elif filter_type == "all":
            pass

        else:
            return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

        query = f"""
            SELECT
                COALESCE(SUM(CASE WHEN w.category = 'Rainy' THEN w.duration ELSE 0 END), 0)::numeric AS rainy,
                COALESCE(SUM(CASE WHEN w.category = 'Slippery' THEN w.duration ELSE 0 END), 0)::numeric AS slippery
            FROM mining_weather w
            {filter_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        rainy = float(row[0] or 0)
        slippery = float(row[1] or 0)

        return JsonResponse({
            "rainy": rainy,
            "slippery": slippery
        })

    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({"error": str(e)}, status=500)
    
def get_data_rainfall(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        filter_sql = "WHERE 1=1"
        params = []

        # FILTER IUP
        iup_clause, iup_params = build_iup_clause(iup_filter, "r")
        filter_sql += iup_clause
        params += iup_params

        # FILTER DATE
        if filter_type == "daily" and filter_date:
            filter_sql += " AND r.date = %s"
            params += [filter_date]

        elif filter_type == "range" and date_start and date_end:
            filter_sql += " AND r.date BETWEEN %s AND %s"
            params += [date_start, date_end]

        elif filter_type == "weekly" and year and month and week:
            try:
                if "-" in str(week):
                    year_str, week_str = str(week).split("-")
                    year = int(year_str)
                    week = int(week_str)

                    start_date = datetime.strptime(f"{year}-W{week:02}-1", "%G-W%V-%u")
                    end_date = start_date + timedelta(days=6)

                else:
                    year = int(year)
                    month = int(month)
                    week = int(week)

                    if not (1 <= month <= 12):
                        return JsonResponse({"error": "Bulan tidak valid (1–12)"}, status=400)
                    if not (1 <= week <= 5):
                        return JsonResponse({"error": "Minggu tidak valid (1–5)"}, status=400)

                    first_day = datetime(year, month, 1)
                    start_date = first_day + timedelta(days=(week - 1) * 7)
                    end_date = start_date + timedelta(days=6)

                    if end_date.month != month:
                        next_month = datetime(year, month, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

            except Exception as e:
                return JsonResponse(
                    {"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"},
                    status=400
                )

            filter_sql += " AND r.date BETWEEN %s AND %s"
            params += [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

        elif filter_type == "monthly" and year and month:
            filter_sql += " AND EXTRACT(YEAR FROM r.date) = %s AND EXTRACT(MONTH FROM r.date) = %s"
            params += [year, month]

        elif filter_type == "yearly" and year:
            filter_sql += " AND EXTRACT(YEAR FROM r.date) = %s"
            params += [year]

        elif filter_type == "all":
            pass

        else:
            return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

        query = f"""
            WITH per_day AS (
                SELECT
                    r.date::date AS date,
                    AVG(r.milimeter)::numeric AS avg_rain
                FROM mining_rainfall r
                {filter_sql}
                GROUP BY r.date::date
            )
            SELECT
                COALESCE(AVG(per_day.avg_rain), 0)::numeric AS milimeter
            FROM per_day
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        milimeter = float(row[0] or 0)

        return JsonResponse({
            "milimeter": milimeter,
        })

    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({"error": str(e)}, status=500)
    
# For Chart
def get_chart_rainfall(request):
    iup_filter   = request.GET.get("iup_id") or request.GET.get("iup_filter")
    filter_type  = request.GET.get('filter_type')
    filter_year  = int(request.GET.get('year', 0))
    filter_month = int(request.GET.get('month', 0))
    filter_week  = request.GET.get('week')
    filter_date  = request.GET.get('filter_date')
    date_start   = request.GET.get('date_start')
    date_end     = request.GET.get('date_end')

    if filter_type == 'monthly' and filter_year and filter_month:
        return get_monthly_chart(filter_year, filter_month,iup_filter)
    
    elif filter_type == 'daily' and filter_date:
        return get_daily_chart(filter_date, iup_filter)

    elif filter_type == 'range' and date_start and date_end:
        return get_range_chart(date_start, date_end, iup_filter)

    elif filter_type == 'yearly' and filter_year:
        return get_yearly_chart(filter_year)

    elif filter_type == "weekly" and filter_year and filter_month and filter_week:
        return get_weekly_chart(filter_year, filter_month, filter_week, iup_filter)

    elif filter_type == 'all':
        return get_all_chart(iup_filter)

    else:
        return JsonResponse({'error': 'Invalid filter'}, status=400)

def get_daily_chart(filter_date, iup_filter=None):
    where_sql = "r.date = %s::date"
    params = [filter_date]

    # FILTER IUP
    iup_clause, iup_params = build_iup_clause(iup_filter, "r")
    where_sql += iup_clause
    params += iup_params

    query = f"""
        SELECT
            TO_CHAR(r.date, 'YYYY-MM-DD') AS label,
            ROUND(COALESCE(SUM(r.milimeter), 0)::numeric, 2) AS total_milimeter
        FROM mining_rainfall r
        WHERE {where_sql}
        GROUP BY r.date
        ORDER BY r.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    if not data:
        return JsonResponse({
            "x_data": [filter_date],
            "y_data": [0.0],
            "grand_total": 0.0,
            "details": []
        }, safe=False)

    df = pd.DataFrame(data, columns=["label", "total_milimeter"])
    df["total_milimeter"] = pd.to_numeric(
        df["total_milimeter"], errors="coerce"
    ).fillna(0.0).round(2)

    grand_total = round(df["total_milimeter"].sum(), 2)

    return JsonResponse({
        "x_data": df["label"].tolist(),
        "y_data": df["total_milimeter"].astype(float).tolist(),
        "grand_total": float(grand_total),
        "details": []
    }, safe=False)

def get_monthly_chart(filter_year, filter_month, iup_filter=None):
    year = int(filter_year)
    month = int(filter_month)

    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    where_date = "r.date BETWEEN %s AND %s"
    date_params = [tgl_pertama, tgl_terakhir]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND r.iup_id IN ({placeholders})"
            date_params += iup_ids

    params = [tgl_pertama, tgl_terakhir, *date_params, *date_params]

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
        ),
        actual_total AS (
            SELECT
                r.date::date AS date,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            WHERE {where_date}
            GROUP BY r.date::date
        ),
        actual_point AS (
            SELECT
                r.date::date AS date,
                COALESCE(rp.name, '-') AS point_name,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            LEFT JOIN mining_rainfall_point rp
                ON rp.id = r.point_id
               AND rp.iup_id = r.iup_id
            WHERE {where_date}
            GROUP BY r.date::date, rp.name
        )
        SELECT
            TO_CHAR(t.date, 'DD') AS left_date,
            ROUND(COALESCE(at.milimeter, 0)::numeric, 2) AS total_milimeter,
            COALESCE(
                json_agg(
                    json_build_object(
                        'point_name', ap.point_name,
                        'milimeter', ROUND(ap.milimeter::numeric, 2)
                    )
                    ORDER BY ap.point_name
                ) FILTER (WHERE ap.point_name IS NOT NULL),
                '[]'::json
            ) AS points
        FROM tanggal t
        LEFT JOIN actual_total at ON t.date = at.date
        LEFT JOIN actual_point ap ON t.date = ap.date
        GROUP BY t.date, at.milimeter
        ORDER BY t.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    details = []
    x_data = []
    y_data = []

    for row in data:
        left_date = row[0]
        total_milimeter = float(row[1] or 0)
        points = row[2] or []

        x_data.append(left_date)
        y_data.append(total_milimeter)

        details.append({
            "label": left_date,
            "total_milimeter": total_milimeter,
            "points": points
        })

    grand_total = round(sum(y_data), 2)

    return JsonResponse({
        "x_data": x_data,
        "y_data": y_data,
        "grand_total": float(grand_total),
        "details": details
    }, safe=False)

def get_weekly_chart(filter_year, filter_month, filter_week, iup_filter=None):
    try:
        if "-" in str(filter_week):
            iso_year, iso_week = parse_iso_week(filter_week)
            start_date = datetime.strptime(f"{iso_year}-W{iso_week:02}-1", "%G-W%V-%u").date()
            end_date = start_date + timedelta(days=6)
        else:
            year = int(filter_year)
            month = int(filter_month)
            week = int(filter_week)

            first_day = date(year, month, 1)
            start_date = first_day + timedelta(days=(week - 1) * 7)
            end_date = start_date + timedelta(days=6)

            if end_date.month != month:
                next_month = datetime(year, month, 28) + timedelta(days=4)
                end_date = (datetime(next_month.year, next_month.month, 1) - timedelta(days=1)).date()

    except Exception as e:
        return JsonResponse({"error": f"Format minggu tidak valid: {str(e)}"}, status=400)

    where_sql = "r.date BETWEEN %s AND %s"
    params = [start_date, end_date]

    iup_clause, iup_params = build_iup_clause(iup_filter, "r")
    where_sql += iup_clause
    params += iup_params

    final_params = [start_date, end_date] + params + params

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
        ),
        actual_total AS (
            SELECT
                r.date::date AS date,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            WHERE {where_sql}
            GROUP BY r.date::date
        ),
        actual_point AS (
            SELECT
                r.date::date AS date,
                COALESCE(rp.name, '-') AS point_name,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            LEFT JOIN mining_rainfall_point rp
                ON rp.id = r.point_id
               AND rp.iup_id = r.iup_id
            WHERE {where_sql}
            GROUP BY r.date::date, rp.name
        )
        SELECT
            TO_CHAR(t.date, 'Dy') AS label,
            ROUND(COALESCE(at.milimeter, 0)::numeric, 2) AS total_milimeter,
            COALESCE(
                json_agg(
                    json_build_object(
                        'point_name', ap.point_name,
                        'milimeter', ROUND(ap.milimeter::numeric, 2)
                    )
                    ORDER BY ap.point_name
                ) FILTER (WHERE ap.point_name IS NOT NULL),
                '[]'::json
            ) AS points
        FROM tanggal t
        LEFT JOIN actual_total at ON t.date = at.date
        LEFT JOIN actual_point ap ON t.date = ap.date
        GROUP BY t.date, at.milimeter
        ORDER BY t.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, final_params)
        rows = cursor.fetchall()

    details = []
    x_data = []
    y_data = []

    for row in rows:
        label = row[0]
        total_milimeter = float(row[1] or 0)
        points = row[2] or []

        x_data.append(label)
        y_data.append(total_milimeter)
        details.append({
            "label": label,
            "total_milimeter": total_milimeter,
            "points": points
        })

    return JsonResponse({
        "x_data": x_data,
        "y_data": y_data,
        "grand_total": float(round(sum(y_data), 2)),
        "details": details
    }, safe=False)

def get_range_chart(date_start, date_end, iup_filter=None):
    where_sql = "r.date BETWEEN %s AND %s"
    params = [date_start, date_end]

    # FILTER IUP
    iup_clause, iup_params = build_iup_clause(iup_filter, "r")
    where_sql += iup_clause
    params += iup_params

    # dipakai 2x: actual_total dan actual_point
    final_params = [date_start, date_end] + params + params

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
        ),
        actual_total AS (
            SELECT
                r.date::date AS date,
                COALESCE(SUM(r.milimeter), 0)::numeric AS total_milimeter
            FROM mining_rainfall r
            WHERE {where_sql}
            GROUP BY r.date::date
        ),
        actual_point AS (
            SELECT
                r.date::date AS date,
                COALESCE(rp.name, '-') AS point_name,
                COALESCE(SUM(r.milimeter), 0)::numeric AS total_milimeter
            FROM mining_rainfall r
            LEFT JOIN mining_rainfall_point rp
                ON rp.id = r.point_id
               AND rp.iup_id = r.iup_id
            WHERE {where_sql}
            GROUP BY r.date::date, rp.name
        )
        SELECT
            TO_CHAR(t.date, 'YYYY-MM-DD') AS label,
            ROUND(COALESCE(at.total_milimeter, 0)::numeric, 2) AS total_milimeter,
            COALESCE(
                json_agg(
                    json_build_object(
                        'point_name', ap.point_name,
                        'milimeter', ROUND(ap.total_milimeter::numeric, 2)
                    )
                    ORDER BY ap.point_name
                ) FILTER (WHERE ap.point_name IS NOT NULL),
                '[]'::json
            ) AS points
        FROM tanggal t
        LEFT JOIN actual_total at ON t.date = at.date
        LEFT JOIN actual_point ap ON t.date = ap.date
        GROUP BY t.date, at.total_milimeter
        ORDER BY t.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, final_params)
        rows = cursor.fetchall()

    x_data = []
    y_data = []
    details = []

    for row in rows:
        label = row[0]
        total_milimeter = float(row[1] or 0)
        points = row[2] or []

        x_data.append(label)
        y_data.append(total_milimeter)
        details.append({
            "label": label,
            "total_milimeter": total_milimeter,
            "points": points
        })

    grand_total = round(sum(y_data), 2)

    return JsonResponse({
        "x_data": x_data,
        "y_data": y_data,
        "grand_total": float(grand_total),
        "details": details
    }, safe=False)

def get_yearly_chart(filter_year, iup_filter=None):
    year = int(filter_year)

    where_sql = "EXTRACT(YEAR FROM r.date) = %s"
    params = [year]

    iup_clause, iup_params = build_iup_clause(iup_filter, "r")
    where_sql += iup_clause
    params += iup_params

    final_params = params + params

    query = f"""
        WITH bulan AS (
            SELECT generate_series(1, 12) AS month_num
        ),
        actual_total AS (
            SELECT
                EXTRACT(MONTH FROM r.date)::int AS month_num,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            WHERE {where_sql}
            GROUP BY EXTRACT(MONTH FROM r.date)
        ),
        actual_point AS (
            SELECT
                EXTRACT(MONTH FROM r.date)::int AS month_num,
                COALESCE(rp.name, '-') AS point_name,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            LEFT JOIN mining_rainfall_point rp
                ON rp.id = r.point_id
               AND rp.iup_id = r.iup_id
            WHERE {where_sql}
            GROUP BY EXTRACT(MONTH FROM r.date), rp.name
        )
        SELECT
            TO_CHAR(TO_DATE(b.month_num::text, 'MM'), 'Mon') AS label,
            ROUND(COALESCE(at.milimeter, 0)::numeric, 2) AS total_milimeter,
            COALESCE(
                json_agg(
                    json_build_object(
                        'point_name', ap.point_name,
                        'milimeter', ROUND(ap.milimeter::numeric, 2)
                    )
                    ORDER BY ap.point_name
                ) FILTER (WHERE ap.point_name IS NOT NULL),
                '[]'::json
            ) AS points
        FROM bulan b
        LEFT JOIN actual_total at ON b.month_num = at.month_num
        LEFT JOIN actual_point ap ON b.month_num = ap.month_num
        GROUP BY b.month_num, at.milimeter
        ORDER BY b.month_num
    """

    with connection.cursor() as cursor:
        cursor.execute(query, final_params)
        rows = cursor.fetchall()

    details = []
    x_data = []
    y_data = []

    for row in rows:
        label = row[0]
        total_milimeter = float(row[1] or 0)
        points = row[2] or []

        x_data.append(label)
        y_data.append(total_milimeter)
        details.append({
            "label": label,
            "total_milimeter": total_milimeter,
            "points": points
        })

    return JsonResponse({
        "x_data": x_data,
        "y_data": y_data,
        "grand_total": float(round(sum(y_data), 2)),
        "details": details
    }, safe=False)

def get_all_chart(iup_filter=None):
    where_sql = "1=1"
    params = []

    iup_clause, iup_params = build_iup_clause(iup_filter, "r")
    where_sql += iup_clause
    params += iup_params

    final_params = params + params

    query = f"""
        WITH tahun AS (
            SELECT DISTINCT EXTRACT(YEAR FROM r.date)::int AS year_num
            FROM mining_rainfall r
            WHERE {where_sql}
        ),
        actual_total AS (
            SELECT
                EXTRACT(YEAR FROM r.date)::int AS year_num,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            WHERE {where_sql}
            GROUP BY EXTRACT(YEAR FROM r.date)
        ),
        actual_point AS (
            SELECT
                EXTRACT(YEAR FROM r.date)::int AS year_num,
                COALESCE(rp.name, '-') AS point_name,
                COALESCE(SUM(r.milimeter), 0)::numeric AS milimeter
            FROM mining_rainfall r
            LEFT JOIN mining_rainfall_point rp
                ON rp.id = r.point_id
               AND rp.iup_id = r.iup_id
            WHERE {where_sql}
            GROUP BY EXTRACT(YEAR FROM r.date), rp.name
        )
        SELECT
            t.year_num::text AS label,
            ROUND(COALESCE(at.milimeter, 0)::numeric, 2) AS total_milimeter,
            COALESCE(
                json_agg(
                    json_build_object(
                        'point_name', ap.point_name,
                        'milimeter', ROUND(ap.milimeter::numeric, 2)
                    )
                    ORDER BY ap.point_name
                ) FILTER (WHERE ap.point_name IS NOT NULL),
                '[]'::json
            ) AS points
        FROM tahun t
        LEFT JOIN actual_total at ON t.year_num = at.year_num
        LEFT JOIN actual_point ap ON t.year_num = ap.year_num
        GROUP BY t.year_num, at.milimeter
        ORDER BY t.year_num
    """

    with connection.cursor() as cursor:
        cursor.execute(query, final_params)
        rows = cursor.fetchall()

    details = []
    x_data = []
    y_data = []

    for row in rows:
        label = row[0]
        total_milimeter = float(row[1] or 0)
        points = row[2] or []

        x_data.append(label)
        y_data.append(total_milimeter)
        details.append({
            "label": label,
            "total_milimeter": total_milimeter,
            "points": points
        })

    return JsonResponse({
        "x_data": x_data,
        "y_data": y_data,
        "grand_total": float(round(sum(y_data), 2)),
        "details": details
    }, safe=False)