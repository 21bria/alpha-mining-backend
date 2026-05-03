# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import pandas as pd
import calendar
from datetime import datetime, timedelta
from django.db.models import Sum
from django.utils.timezone import now
from django.db.models.functions import TruncWeek
logger = logging.getLogger(__name__) #tambahkan ini untuk multi database.
import json

class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def to_float1(v):
    return round(float(v or 0), 1)

def get_month_label(month_number):
    month_labels = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    return month_labels.get(month_number, '')

# Card Summary
def build_summary_query(where_clause: str) -> str:
    return f"""
        SELECT 
            COALESCE(
                ROUND(
                    SUM(CASE WHEN nama_material IN ('LIM', 'SAP') THEN tonnage ELSE 0 END)::numeric,
                    2
                ),
                0
            ) AS total,
            COALESCE(
                ROUND(
                    SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric,
                    2
                ),
                0
            ) AS total_lim,
            COALESCE(
                ROUND(
                    SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric,
                    2
                ),
                0
            ) AS total_sap
        FROM view_geology_ore_production
        {where_clause}
    """

def get_ore_summary(request):
    try:
        iup_filter = request.GET.get("iup_id")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        where_clause = "WHERE 1=1"
        params = []

        # filter iup
        if iup_filter:
            iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
            if iup_ids:
                placeholders = ",".join(["%s"] * len(iup_ids))
                where_clause += f" AND iup_id IN ({placeholders})"
                params += iup_ids

        # filter tanggal
        if filter_type == "daily" and filter_date:
            where_clause += " AND tgl_production = %s"
            params += [filter_date]

        elif filter_type == "range" and date_start and date_end:
            where_clause += " AND tgl_production BETWEEN %s AND %s"
            params += [date_start, date_end]

        elif filter_type == "weekly" and week:
            where_clause += " AND TO_CHAR(tgl_production, 'IYYY-IW') = %s"
            params += [week]

        elif filter_type == "monthly" and year and month:
            where_clause += """
                AND EXTRACT(YEAR FROM tgl_production) = %s
                AND EXTRACT(MONTH FROM tgl_production) = %s
            """
            params += [year, month]

        elif filter_type == "yearly" and year:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s"
            params += [year]

        elif filter_type == "all" or not filter_type:
            pass

        else:
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
        logger.exception("Unexpected error in get_ore_summary")
        return JsonResponse({"error": str(e)}, status=500)
    
# Create Chart Ore
def get_chart_ore(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")

        x_labels = []
        data_lim = []
        data_sap = []

        def build_iup_clause(iup_filter_value):
            if not iup_filter_value:
                return "", []

            iup_ids = [x.strip() for x in str(iup_filter_value).split(",") if x.strip()]
            if not iup_ids:
                return "", []

            placeholders = ",".join(["%s"] * len(iup_ids))
            return f" AND iup_id IN ({placeholders})", iup_ids

        iup_clause, iup_params = build_iup_clause(iup_filter)

        if filter_type == "range" and date_start and date_end:
            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                incoming AS (
                    SELECT
                        tgl_production::date AS date,
                        SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap
                    FROM view_geology_ore_production
                    WHERE tgl_production BETWEEN %s AND %s
                    {iup_clause}
                    GROUP BY tgl_production
                )
                SELECT
                    TO_CHAR(tanggal.date, 'YYYY-MM-DD') AS label,
                    COALESCE(i.lim, 0) AS lim,
                    COALESCE(i.sap, 0) AS sap
                FROM tanggal
                LEFT JOIN incoming i ON tanggal.date = i.date
                ORDER BY tanggal.date
            """
            params = [date_start, date_end, date_start, date_end, *iup_params]

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
                return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                incoming AS (
                    SELECT
                        tgl_production::date AS date,
                        TRIM(TO_CHAR(tgl_production, 'Day')) AS day,
                        SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap
                    FROM view_geology_ore_production
                    WHERE tgl_production BETWEEN %s AND %s
                    {iup_clause}
                    GROUP BY tgl_production
                ),
                combine AS (
                    SELECT
                        tanggal.date,
                        TRIM(TO_CHAR(tanggal.date, 'Day')) AS day_name,
                        COALESCE(i.lim, 0) AS lim,
                        COALESCE(i.sap, 0) AS sap
                    FROM tanggal
                    LEFT JOIN incoming i ON tanggal.date = i.date
                )
                SELECT
                    day_name AS label,
                    SUM(lim) AS lim,
                    SUM(sap) AS sap
                FROM combine
                GROUP BY day_name
                ORDER BY ARRAY_POSITION(
                    ARRAY['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
                    day_name
                )
            """
            params = [
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                *iup_params,
            ]

        elif filter_type == "monthly" and year and month:
            year = int(year)
            month = int(month)
            last_day = calendar.monthrange(year, month)[1]
            tgl_pertama = datetime(year, month, 1).date()
            tgl_terakhir = datetime(year, month, last_day).date()

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                incoming AS (
                    SELECT
                        tgl_production::date AS date,
                        SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap
                    FROM view_geology_ore_production
                    WHERE tgl_production BETWEEN %s AND %s
                    {iup_clause}
                    GROUP BY tgl_production
                )
                SELECT
                    TO_CHAR(tanggal.date, 'DD') AS label,
                    COALESCE(i.lim, 0) AS lim,
                    COALESCE(i.sap, 0) AS sap
                FROM tanggal
                LEFT JOIN incoming i ON tanggal.date = i.date
                ORDER BY tanggal.date
            """
            params = [tgl_pertama, tgl_terakhir, tgl_pertama, tgl_terakhir, *iup_params]

        elif filter_type == "yearly" and year:
            query = f"""
                WITH bulan AS (
                    SELECT generate_series(1, 12) AS month
                ),
                incoming AS (
                    SELECT
                        EXTRACT(MONTH FROM tgl_production)::int AS month,
                        SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap
                    FROM view_geology_ore_production
                    WHERE EXTRACT(YEAR FROM tgl_production) = %s
                    {iup_clause}
                    GROUP BY EXTRACT(MONTH FROM tgl_production)
                )
                SELECT
                    TO_CHAR(TO_DATE(bulan.month::text, 'MM'), 'Mon ') AS label,
                    COALESCE(i.lim, 0) AS lim,
                    COALESCE(i.sap, 0) AS sap
                FROM bulan
                LEFT JOIN incoming i ON bulan.month = i.month
                ORDER BY bulan.month
            """
            params = [year, *iup_params]

        elif filter_type == "all":
            query = f"""
                SELECT
                    TO_CHAR(tgl_production, 'YYYY') AS label,
                    SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim,
                    SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap
                FROM view_geology_ore_production
                WHERE 1=1
                {iup_clause}
                GROUP BY TO_CHAR(tgl_production, 'YYYY')
                ORDER BY TO_CHAR(tgl_production, 'YYYY')
            """
            params = [*iup_params]

        else:
            return JsonResponse({"error": "Invalid filter"}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        for row in results:
            x_labels.append(str(row[0]))
            data_lim.append(round(float(row[1] or 0), 2))
            data_sap.append(round(float(row[2] or 0), 2))

        return JsonResponse({
            "x_data": x_labels,
            "y_data_lim": data_lim,
            "y_data_sap": data_sap,
        })

    except DatabaseError:
        logger.exception("DB Error in get_chart_ore")
        return JsonResponse({"error": "Database error"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error in get_chart_ore")
        return JsonResponse({"error": str(e)}, status=500)
    
def get_ore_class(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        filter_sql = "WHERE 1=1"
        params = []

        # filter iup
        if iup_filter:
            iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
            if iup_ids:
                placeholders = ",".join(["%s"] * len(iup_ids))
                filter_sql += f" AND iup_id IN ({placeholders})"
                params += iup_ids

        # filter tanggal
        if filter_type == "daily" and filter_date:
            filter_sql += " AND tgl_production = %s"
            params += [filter_date]

        elif filter_type == "range" and date_start and date_end:
            filter_sql += " AND tgl_production BETWEEN %s AND %s"
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

            filter_sql += " AND tgl_production BETWEEN %s AND %s"
            params += [
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            ]

        elif filter_type == "monthly" and year and month:
            filter_sql += """
                AND EXTRACT(YEAR FROM tgl_production) = %s
                AND EXTRACT(MONTH FROM tgl_production) = %s
            """
            params += [year, month]

        elif filter_type == "yearly" and year:
            filter_sql += " AND EXTRACT(YEAR FROM tgl_production) = %s"
            params += [year]

        elif filter_type == "all":
            pass

        else:
            return JsonResponse(
                {"error": "Invalid or incomplete filter parameters"},
                status=400
            )

        query = f"""
            SELECT
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'LGL' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS lglo,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'MGL' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS mglo,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'HGL' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS hglo,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'LGS' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS lgso,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'MGS' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS mgso,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'HGS' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS hgso
            FROM view_geology_ore_production
            {filter_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            chart_data = cursor.fetchone()

        y_data = [float(val or 0) for val in chart_data] if chart_data else [0, 0, 0, 0, 0, 0]

        return JsonResponse({
            "labels": ["LGLO", "MGLO", "HGLO", "LGSO", "MGSO", "HGSO"],
            "y_data": y_data,
        })

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Internal server error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({"error": str(e)}, status=500)