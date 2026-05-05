# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import pandas as pd
import calendar
from datetime import datetime, timedelta
from decimal import Decimal
from analytics.services.iup_filter import build_iup_clause
logger = logging.getLogger(__name__)

def to_float1(v):
    return round(float(v or 0), 1)

def decimal_to_float(value):
    return float(value) if isinstance(value, Decimal) else value
# Card Summary
def build_summary_query(where_clause: str) -> str:
    return f"""
        SELECT 
            COALESCE(
                ROUND(SUM(CASE WHEN vsd.sale_adjust IN ('HPAL', 'RKEF') THEN vsd.tonnage ELSE 0 END)::numeric, 2),
                0
            ) AS total,
            COALESCE(
                ROUND(SUM(CASE WHEN vsd.sale_adjust = 'HPAL' THEN vsd.tonnage ELSE 0 END)::numeric, 2),
                0
            ) AS total_lim,
            COALESCE(
                ROUND(SUM(CASE WHEN vsd.sale_adjust = 'RKEF' THEN vsd.tonnage ELSE 0 END)::numeric, 2),
                0
            ) AS total_sap
        FROM view_selling_details vsd
        {where_clause}
    """

def get_selling_summary(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        where_clause = "WHERE 1=1"
        params = []

        # Filter status barging hanya Complete
        where_clause += " AND vsd.status_barging = %s"
        params.append("Complete")

        # Filter IUP
        iup_clause, iup_params = build_iup_clause(iup_filter, "vsd")
        where_clause += iup_clause
        params += iup_params

        # Filter periode
        if filter_type == "daily" and filter_date:
            where_clause += " AND vsd.date_barge_out = %s"
            params.append(filter_date)

        elif filter_type == "range" and date_start and date_end:
            where_clause += " AND vsd.date_barge_out BETWEEN %s AND %s"
            params += [date_start, date_end]

        elif filter_type == "weekly" and week:
            where_clause += " AND TO_CHAR(vsd.date_barge_out, 'IYYY-IW') = %s"
            params.append(week)

        elif filter_type == "monthly" and year and month:
            where_clause += """
                AND EXTRACT(YEAR FROM vsd.date_barge_out) = %s
                AND EXTRACT(MONTH FROM vsd.date_barge_out) = %s
            """
            params += [year, month]

        elif filter_type == "yearly" and year:
            where_clause += " AND EXTRACT(YEAR FROM vsd.date_barge_out) = %s"
            params.append(year)

        elif filter_type == "all":
            pass

        elif filter_type not in ["daily", "range", "weekly", "monthly", "yearly", "all", None, ""]:
            return JsonResponse({"error": "Invalid filter type"}, status=400)

        query = build_summary_query(where_clause)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        return JsonResponse({
            "total_ore": to_float1(row[0]),
            "total_lim": to_float1(row[1]),
            "total_sap": to_float1(row[2]),
        })

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in get_selling_summary")
        return JsonResponse({"error": str(e)}, status=500)
    
# Create Chart selling
def get_chart_selling(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        query = None
        params = []

        # daily
        if filter_type == "daily" and filter_date:
            iup_clause, iup_params = build_iup_clause(iup_filter, "s")

            query = f"""
                WITH working_hours AS (
                    SELECT
                        hour_label,
                        CASE
                            WHEN hour_label >= 7 THEN hour_label
                            ELSE hour_label + 24
                        END AS sort_order
                    FROM generate_series(0, 23) AS hour_label
                ),
                actual_daily AS (
                    SELECT
                        COALESCE(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END), 0) AS actual_lim,
                        COALESCE(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END), 0) AS actual_sap
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND DATE(s.date_barge_out) = %s::date
                ),
                actual_hourly AS (
                    SELECT
                        wh.hour_label,
                        (ad.actual_lim / 22.0) AS actual_lim,
                        (ad.actual_sap / 22.0) AS actual_sap
                    FROM working_hours wh
                    CROSS JOIN actual_daily ad
                    WHERE wh.hour_label BETWEEN 7 AND 23
                       OR wh.hour_label BETWEEN 0 AND 4
                )
                SELECT
                    wh.hour_label AS label,
                    COALESCE(a.actual_lim, 0) + COALESCE(a.actual_sap, 0) AS actual_total,
                    COALESCE(a.actual_lim, 0) AS actual_lim,
                    COALESCE(a.actual_sap, 0) AS actual_sap,
                    '[]'::json AS barges
                FROM working_hours wh
                LEFT JOIN actual_hourly a ON a.hour_label = wh.hour_label
                WHERE wh.hour_label BETWEEN 7 AND 23
                   OR wh.hour_label BETWEEN 0 AND 4
                ORDER BY wh.sort_order
            """
            params = [*iup_params, filter_date]

        # range
        elif filter_type == "range" and date_start and date_end:
            iup_clause, iup_params = build_iup_clause(iup_filter, "s")

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
                ),
                actual AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END) AS sap
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND s.date_barge_out::date BETWEEN %s::date AND %s::date
                    GROUP BY s.date_barge_out::date
                ),
                detail AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        mb.barge_code,
                        SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END) AS sap,
                        SUM(s.tonnage) AS total
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND s.date_barge_out::date BETWEEN %s::date AND %s::date
                    GROUP BY s.date_barge_out::date, mb.barge_code
                )
                SELECT
                    TO_CHAR(t.date, 'YYYY-MM-DD') AS label,
                    COALESCE(a.lim, 0) + COALESCE(a.sap, 0) AS actual_total,
                    COALESCE(a.lim, 0) AS actual_lim,
                    COALESCE(a.sap, 0) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'lim', d.lim,
                                'sap', d.sap,
                                'total', d.total
                            )
                            ORDER BY d.barge_code
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS barges
                FROM tanggal t
                LEFT JOIN actual a ON t.date = a.date
                LEFT JOIN detail d ON t.date = d.date
                GROUP BY t.date, a.lim, a.sap
                ORDER BY t.date
            """
            params = [
                date_start, date_end,
                *iup_params, date_start, date_end,
                *iup_params, date_start, date_end,
            ]

        # weekly
        elif filter_type == "weekly" and week:
            try:
                if "-" in str(week):
                    year_str, week_str = str(week).split("-")
                    iso_year = int(year_str)
                    iso_week = int(week_str)

                    start_date_obj = datetime.strptime(f"{iso_year}-W{iso_week:02}-1", "%G-W%V-%u")
                    end_date_obj = start_date_obj + timedelta(days=6)
                else:
                    year_int = int(year)
                    month_int = int(month)
                    week_int = int(week)

                    if not (1 <= month_int <= 12):
                        return JsonResponse({"error": "Bulan tidak valid (1-12)"}, status=400)
                    if not (1 <= week_int <= 5):
                        return JsonResponse({"error": "Minggu tidak valid (1-5)"}, status=400)

                    first_day = datetime(year_int, month_int, 1)
                    start_date_obj = first_day + timedelta(days=(week_int - 1) * 7)
                    end_date_obj = start_date_obj + timedelta(days=6)

                    if end_date_obj.month != month_int:
                        next_month = datetime(year_int, month_int, 28) + timedelta(days=4)
                        end_date_obj = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

            except Exception as e:
                return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)

            start_date_str = start_date_obj.strftime("%Y-%m-%d")
            end_date_str = end_date_obj.strftime("%Y-%m-%d")

            iup_clause, iup_params = build_iup_clause(iup_filter, "s")

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
                ),
                actual AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END) AS actual_lim,
                        SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END) AS actual_sap
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND s.date_barge_out::date BETWEEN %s::date AND %s::date
                    GROUP BY s.date_barge_out::date
                ),
                detail AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        mb.barge_code,
                        SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END) AS sap,
                        SUM(s.tonnage) AS total
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND s.date_barge_out::date BETWEEN %s::date AND %s::date
                    GROUP BY s.date_barge_out::date, mb.barge_code
                ),
                combine AS (
                    SELECT
                        t.date,
                        TO_CHAR(t.date, 'FMDay') AS day_name,
                        COALESCE(a.actual_lim, 0) AS actual_lim,
                        COALESCE(a.actual_sap, 0) AS actual_sap,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'barge_code', d.barge_code,
                                    'lim', d.lim,
                                    'sap', d.sap,
                                    'total', d.total
                                )
                                ORDER BY d.barge_code
                            ) FILTER (WHERE d.barge_code IS NOT NULL),
                            '[]'::json
                        ) AS barges
                    FROM tanggal t
                    LEFT JOIN actual a ON t.date = a.date
                    LEFT JOIN detail d ON t.date = d.date
                    GROUP BY t.date, day_name, a.actual_lim, a.actual_sap
                )
                SELECT
                    day_name AS label,
                    SUM(actual_lim + actual_sap) AS actual_total,
                    SUM(actual_lim) AS actual_lim,
                    SUM(actual_sap) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'date', TO_CHAR(date, 'YYYY-MM-DD'),
                                'lim', actual_lim,
                                'sap', actual_sap,
                                'total', actual_lim + actual_sap,
                                'barges', barges
                            )
                            ORDER BY date
                        ),
                        '[]'::json
                    ) AS barges
                FROM combine
                GROUP BY day_name
                ORDER BY ARRAY_POSITION(
                    ARRAY['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
                    day_name
                )
            """
            params = [
                start_date_str, end_date_str,
                *iup_params, start_date_str, end_date_str,
                *iup_params, start_date_str, end_date_str,
            ]

        # monthly
        elif filter_type == "monthly" and year and month:
            year_int = int(year)
            month_int = int(month)
            last_day = calendar.monthrange(year_int, month_int)[1]

            tgl_pertama = datetime(year_int, month_int, 1).date()
            tgl_terakhir = datetime(year_int, month_int, last_day).date()

            iup_clause, iup_params = build_iup_clause(iup_filter, "s")

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
                ),
                summary AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND s.date_barge_out::date BETWEEN %s::date AND %s::date
                    GROUP BY s.date_barge_out::date
                ),
                detail AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        mb.barge_code,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND s.date_barge_out::date BETWEEN %s::date AND %s::date
                    GROUP BY s.date_barge_out::date, mb.barge_code
                )
                SELECT
                    TO_CHAR(t.date, 'DD') AS label,
                    COALESCE(s.total, 0) AS actual_total,
                    COALESCE(s.lim, 0) AS actual_lim,
                    COALESCE(s.sap, 0) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'lim', d.lim,
                                'sap', d.sap,
                                'total', d.total
                            )
                            ORDER BY d.barge_code
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS barges
                FROM tanggal t
                LEFT JOIN summary s ON t.date = s.date
                LEFT JOIN detail d ON t.date = d.date
                GROUP BY t.date, s.total, s.lim, s.sap
                ORDER BY t.date
            """
            params = [
                tgl_pertama, tgl_terakhir,
                *iup_params, tgl_pertama, tgl_terakhir,
                *iup_params, tgl_pertama, tgl_terakhir,
            ]

        # yearly
        elif filter_type == "yearly" and year:
            iup_clause, iup_params = build_iup_clause(iup_filter, "s")

            query = f"""
                WITH bulan AS (
                    SELECT generate_series(1, 12) AS month
                ),
                summary AS (
                    SELECT
                        EXTRACT(MONTH FROM s.date_barge_out)::int AS month,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND EXTRACT(YEAR FROM s.date_barge_out) = %s
                    GROUP BY EXTRACT(MONTH FROM s.date_barge_out)
                ),
                detail AS (
                    SELECT
                        EXTRACT(MONTH FROM s.date_barge_out)::int AS month,
                        mb.barge_code,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    AND EXTRACT(YEAR FROM s.date_barge_out) = %s
                    GROUP BY EXTRACT(MONTH FROM s.date_barge_out), mb.barge_code
                )
                SELECT
                    TO_CHAR(TO_DATE(b.month::text, 'MM'), 'Mon') AS label,
                    COALESCE(s.total, 0)::float AS actual_total,
                    COALESCE(s.lim, 0)::float AS actual_lim,
                    COALESCE(s.sap, 0)::float AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'lim', d.lim,
                                'sap', d.sap,
                                'total', d.total
                            )
                            ORDER BY d.barge_code
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS barges
                FROM bulan b
                LEFT JOIN summary s ON b.month = s.month
                LEFT JOIN detail d ON b.month = d.month
                GROUP BY b.month, s.total, s.lim, s.sap
                ORDER BY b.month
            """
            params = [
                *iup_params, year,
                *iup_params, year,
            ]

        # all
        elif filter_type == "all":
            iup_clause, iup_params = build_iup_clause(iup_filter, "s")

            query = f"""
                WITH tahun AS (
                    SELECT generate_series(
                        (
                            SELECT MIN(EXTRACT(YEAR FROM s.date_barge_out))::int
                            FROM selling_barging s
                            WHERE s.status_barging = 'Complete'
                            {iup_clause}
                        ),
                        (
                            SELECT MAX(EXTRACT(YEAR FROM s.date_barge_out))::int
                            FROM selling_barging s
                            WHERE s.status_barging = 'Complete'
                            {iup_clause}
                        )
                    ) AS year
                ),
                summary AS (
                    SELECT
                        EXTRACT(YEAR FROM s.date_barge_out)::int AS year,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    GROUP BY EXTRACT(YEAR FROM s.date_barge_out)
                ),
                detail AS (
                    SELECT
                        EXTRACT(YEAR FROM s.date_barge_out)::int AS year,
                        mb.barge_code,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    WHERE s.status_barging = 'Complete'
                    {iup_clause}
                    GROUP BY EXTRACT(YEAR FROM s.date_barge_out), mb.barge_code
                )
                SELECT
                    t.year::text AS label,
                    COALESCE(s.total, 0)::float AS actual_total,
                    COALESCE(s.lim, 0)::float AS actual_lim,
                    COALESCE(s.sap, 0)::float AS actual_sap,
                     '[]'::json AS barges  
                FROM tahun t
                LEFT JOIN summary s ON t.year = s.year
                LEFT JOIN detail d ON t.year = d.year
                GROUP BY t.year, s.total, s.lim, s.sap
                ORDER BY t.year
            """
            params = [
                *iup_params,
                *iup_params,
                *iup_params,
                *iup_params,
            ]

        else:
            return JsonResponse({"error": "Invalid filter type or missing required params"}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        def round_barges(barges_list):
            for b in barges_list:
                for key in ["lim", "sap", "total"]:
                    if key in b and b[key] is not None:
                        b[key] = round(float(b[key]), 1)
                if "barges" in b and isinstance(b["barges"], list):
                    round_barges(b["barges"])

        details = []

        for row in results:
            barges = row[4] if row[4] else []
            round_barges(barges)

            details.append({
                "label": str(row[0]),
                "total_actual": round(float(row[1] or 0), 1),
                "lim_actual": round(float(row[2] or 0), 1),
                "sap_actual": round(float(row[3] or 0), 1),
                "barges": barges,
            })

        return JsonResponse({
            "summary": {
                "x_data": [d["label"] for d in details],
                "y_data_actual": [d["total_actual"] for d in details],
                "y_data_lim": [d["lim_actual"] for d in details],
                "y_data_sap": [d["sap_actual"] for d in details],
            },
            "details": details,
        })

    except DatabaseError:
        logger.exception("DB Error in chart selling")
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in chart selling")
        return JsonResponse({"error": str(e)}, status=500)


# Selling Overview
def summary_selling_overview(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        # Resolve Date Range
        if filter_type == "daily" and filter_date:
            ds = de = filter_date

        elif filter_type == "range" and date_start and date_end:
            ds, de = date_start, date_end

        elif filter_type == "monthly" and year and month:
            year = int(year)
            month = int(month)
            last_day = calendar.monthrange(year, month)[1]
            ds = f"{year}-{month:02d}-01"
            de = f"{year}-{month:02d}-{last_day:02d}"

        elif filter_type == "yearly" and year:
            year = int(year)
            ds = f"{year}-01-01"
            de = f"{year}-12-31"

        elif filter_type == "weekly" and week:
            if "-" in str(week):
                y_str, w_str = str(week).split("-")
                start = datetime.strptime(f"{int(y_str)}-W{int(w_str):02d}-1", "%G-W%V-%u")
                end = start + timedelta(days=6)
            else:
                year = int(year)
                month = int(month)
                week = int(week)

                first_day = datetime(year, month, 1)
                start = first_day + timedelta(days=(week - 1) * 7)
                end = start + timedelta(days=6)

                if end.month != month:
                    end = datetime(year, month, calendar.monthrange(year, month)[1])

            ds = start.strftime("%Y-%m-%d")
            de = end.strftime("%Y-%m-%d")

        elif filter_type == "all":
            ds = "2000-01-01"
            de = "2100-12-31"

        else:
            return JsonResponse({"error": "Invalid filter"}, status=400)

        # IUP Filter
        iup_clause_s, iup_params_s = build_iup_clause(iup_filter, "s")

        query = f"""
            WITH barge_group AS (
                SELECT
                    mb.barge_code,
                    SUM(s.tonnage) AS total_tonnage,
                    ROUND(SUM(CASE WHEN s.sale_adjust = 'HPAL' THEN s.tonnage ELSE 0 END)::numeric, 2) AS total_lim,
                    ROUND(SUM(CASE WHEN s.sale_adjust = 'RKEF' THEN s.tonnage ELSE 0 END)::numeric, 2) AS total_sap
                FROM selling_barging s
                LEFT JOIN master_barge mb ON mb.id = s.barge_code
                LEFT JOIN master_materials m ON m.id = s.id_material
                WHERE 
                    s.status_barging = 'Complete'
                    AND s.date_barge_out BETWEEN %s AND %s
                    {iup_clause_s}
                GROUP BY mb.barge_code
            )
            SELECT
                COALESCE(COUNT(DISTINCT barge_code), 0) AS total_barge,
                COALESCE(SUM(total_tonnage), 0) AS total_ore,
                COALESCE(SUM(total_lim), 0) AS total_lim,
                COALESCE(SUM(total_sap), 0) AS total_sap,

                COALESCE(
                    ROUND(
                        (SUM(total_tonnage) / NULLIF(COUNT(DISTINCT barge_code), 0))::numeric,
                        2
                    ),
                    0
                ) AS avg_mt,

                COALESCE(
                    json_agg(
                        json_build_object(
                            'barge_code', barge_code,
                            'tonnage', ROUND(total_tonnage::numeric, 2),
                            'lim', ROUND(total_lim::numeric, 2),
                            'sap', ROUND(total_sap::numeric, 2)
                        )
                        ORDER BY total_tonnage DESC
                    ) FILTER (WHERE barge_code IS NOT NULL),
                    '[]'::json
                ) AS barges
            FROM barge_group;
        """

        params = [ds, de] + iup_params_s

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        return JsonResponse({
            "total_barge": int(row[0] or 0),
            "total_ore": float(row[1] or 0),
            "total_lim": float(row[2] or 0),
            "total_sap": float(row[3] or 0),
            "avg_mt": float(row[4] or 0),
            "barges": row[5] or [],
            "meta": {
                "date_start": ds,
                "date_end": de,
                "filter_type": filter_type,
            }
        })

    except DatabaseError:
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)