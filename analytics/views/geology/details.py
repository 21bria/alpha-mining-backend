# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
logger = logging.getLogger(__name__) 


def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

def get_start_end_of_week(iso_week_str):
    year, week = map(int, iso_week_str.split('-'))
    start = datetime.strptime(f'{year}-W{week - 1}-1', "%Y-W%W-%w").date()
    end = start + timedelta(days=6)
    return start, end

# For Chart
def get_chart_detail_geology(request):
    iup_filter   = request.GET.get("iup_id")
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
        return get_daily_chart(filter_date)

    elif filter_type == 'range' and date_start and date_end:
        return get_range_chart(date_start, date_end,iup_filter)

    elif filter_type == 'yearly' and filter_year:
        return get_yearly_chart(filter_year,iup_filter)

    elif filter_type == 'weekly' and filter_week:
        return get_weekly_chart(filter_week,iup_filter)

    else:
        return JsonResponse({'error': 'Invalid filter'}, status=400)

def get_daily_chart(filter_date,iup_filter=None):
    where_actual = "mp.date_production = %s::date"
    where_plan = "date_plan = %s::date"

    actual_params = [filter_date]
    plan_params = [filter_date]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND mp.iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

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
        hour_series AS (
            SELECT 
                make_time(hour_label, 0, 0) AS raw_time,
                TO_CHAR(make_time(hour_label, 0, 0), 'HH24') AS left_time,
                hour_label,
                sort_order
            FROM working_hours
        ),
        agg_data AS (
            SELECT 
                LPAD(t_load::text, 2, '0') AS t_load_time,
                SUM(CASE WHEN mp.nama_material = 'LIM' THEN mp.tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN mp.nama_material = 'SAP' THEN mp.tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions mp
            WHERE {where_actual}
            GROUP BY LPAD(t_load::text, 2, '0')
        ),
        plan_per_hour AS (
            SELECT
                SUM(COALESCE(lim,0) + COALESCE(sap,0))::numeric / 22 AS plan_data
            FROM mining_plan_productions
            WHERE {where_plan}
        )
        SELECT
            hs.hour_label AS id,
            hs.left_time,
            COALESCE(agg.lim, 0) AS lim,
            COALESCE(agg.sap, 0) AS sap,
            COALESCE(agg.lim, 0) + COALESCE(agg.sap, 0) AS total,
            p.plan_data
        FROM hour_series hs
        LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
        CROSS JOIN plan_per_hour p
        ORDER BY hs.sort_order;
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'left_time', 'lim', 'sap', 'total', 'plan_data'])

    for col in ['lim', 'sap', 'total', 'plan_data']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    df['achievement'] = df.apply(
        lambda r: round((r['total'] / r['plan_data'] * 100), 2) if r['plan_data'] > 0 else 0.0,
        axis=1
    )

    # === Grand Total per tanggal ===
    grand_total = {
        'lim'   : round(df['lim'].sum(), 2),
        'sap'   : round(df['sap'].sum(), 2),
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement': round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }

    return JsonResponse({
        'x_data'       : df['left_time'].tolist(),
        'lim_actual'   : df['lim'].tolist(),
        'sap_actual'   : df['sap'].tolist(),
        'total_actual' : df['total'].tolist(),
        'total_plan'   : df['plan_data'].tolist(),
        'achievement'  : df['achievement'].tolist(),
        'grand_total'  : grand_total,
    }, safe=False)

def get_monthly_chart(filter_year, filter_month,iup_filter=None):
    # Ambil jumlah hari terakhir dalam bulan
    # last_day = calendar.monthrange(int(filter_year), int(filter_month))[1]

    year = int(filter_year)
    month = int(filter_month)
    # Ambil jumlah hari terakhir dalam bulan
    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    where_actual = "tgl_production BETWEEN %s AND %s"

    actual_params = [tgl_pertama, tgl_terakhir]

    
    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    # params untuk generate_series + actual + plan
    params = [
        tgl_pertama, tgl_terakhir,
        *actual_params
    ]

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
                WHERE {where_actual}
                GROUP BY tgl_production
            )
            SELECT
                TO_CHAR(tanggal.date, 'DD') AS label,
                COALESCE(i.lim, 0) AS lim,
                COALESCE(i.sap, 0) AS lim
            FROM tanggal
            LEFT JOIN incoming i ON tanggal.date = i.date
            ORDER BY tanggal.date
        """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['label', 'lim','sap'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_lim'] = pd.to_numeric(df['lim'], errors='coerce').fillna(0.0).round(2)
    df['total_sap'] = pd.to_numeric(df['sap'], errors='coerce').fillna(0.0).round(2)


    return JsonResponse({
        'x_data': df['label'].tolist(),
        'y_lim': df['total_lim'].astype(float).tolist(),
        'y_sap': df['total_sap'].astype(float).tolist(),
    }, safe=False)

def get_weekly_chart(filter_week, iup_filter=None):
    iso_year, iso_week = map(int, filter_week.split('-'))

    start_date = date.fromisocalendar(iso_year, iso_week, 1)
    end_date = date.fromisocalendar(iso_year, iso_week, 7)

    where_actual = "TO_CHAR(tgl_production, 'IYYY-IW') = %s"
    actual_params = [filter_week]

    # FILTER IUP
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids

    params = [
        start_date,
        end_date,
        *actual_params,
    ]

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
        ),
        incoming AS (
            SELECT
                tgl_production::date AS date,
                TO_CHAR(tgl_production, 'FMDy') AS hari,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap
            FROM view_geology_ore_production
            WHERE {where_actual}
            GROUP BY tgl_production::date, TO_CHAR(tgl_production, 'FMDy')
        )
        SELECT
            TO_CHAR(tanggal.date, 'FMDy') AS hari,
            tanggal.date,
            COALESCE(i.lim, 0)::numeric AS lim,
            COALESCE(i.sap, 0)::numeric AS sap
        FROM tanggal
        LEFT JOIN incoming i ON tanggal.date = i.date
        ORDER BY tanggal.date;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=["label", "date", "lim", "sap"])
    df["total_lim"] = pd.to_numeric(df["lim"], errors="coerce").fillna(0.0).round(2)
    df["total_sap"] = pd.to_numeric(df["sap"], errors="coerce").fillna(0.0).round(2)

    grand_total = {
        "lim": round(df["total_lim"].sum(), 2),
        "sap": round(df["total_sap"].sum(), 2),
        "total": round((df["total_lim"] + df["total_sap"]).sum(), 2),
        "avg_lim": round(df["total_lim"].mean(), 2) if not df.empty else 0.0,
        "avg_sap": round(df["total_sap"].mean(), 2) if not df.empty else 0.0,
    }

    return JsonResponse({
        "x_data": df["label"].astype(str).tolist(),
        "y_lim": df["total_lim"].astype(float).tolist(),
        "y_sap": df["total_sap"].astype(float).tolist(),
        "grand_total": grand_total,
    }, safe=False)

def get_range_chart(date_start, date_end,iup_filter=None):
    where_actual = "tgl_production BETWEEN %s AND %s"

    actual_params = [date_start, date_end]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    params = [
        date_start, date_end,
        *actual_params
    ]

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
            WHERE {where_actual}
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

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['label', 'lim','sap'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_lim'] = pd.to_numeric(df['lim'], errors='coerce').fillna(0.0).round(2)
    df['total_sap'] = pd.to_numeric(df['sap'], errors='coerce').fillna(0.0).round(2)

    return JsonResponse({

        'x_data': df['label'].tolist(),
        'y_lim' : df['total_lim'].astype(float).tolist(),
        'y_sap' : df['total_sap'].astype(float).tolist(),
    }, safe=False)

def get_yearly_chart(filter_yearly,iup_filter=None):
    where_actual = "EXTRACT(YEAR FROM tgl_production) = %s"

    actual_params = [filter_yearly]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids

    params = [
        f"{filter_yearly}-01-01",
        *actual_params,
    ]

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
                WHERE {where_actual}
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

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['label', 'lim','sap'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_lim'] = pd.to_numeric(df['lim'], errors='coerce').fillna(0.0).round(2)
    df['total_sap'] = pd.to_numeric(df['sap'], errors='coerce').fillna(0.0).round(2)

    return JsonResponse({
        'x_data': df['label'].tolist(),
        'y_lim' : df['total_lim'].astype(float).tolist(),
        'y_sap' : df['total_sap'].astype(float).tolist(),
    }, safe=False)

# Class Ore
def get_ore_class_lim(request):
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
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'HGL' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS hglo
            FROM view_geology_ore_production
            {filter_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            chart_data = cursor.fetchone()

        y_data = [float(val or 0) for val in chart_data] if chart_data else [0, 0, 0]

        return JsonResponse({
            "labels": ["LGLO", "MGLO", "HGLO"],
            "y_data": y_data,
        })

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Internal server error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({"error": str(e)}, status=500)
    
def get_ore_class_sap(request):
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

        # =========================
        # FILTER IUP
        # =========================
        if iup_filter:
            iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
            if iup_ids:
                placeholders = ",".join(["%s"] * len(iup_ids))
                filter_sql += f" AND iup_id IN ({placeholders})"
                params += iup_ids

        # =========================
        # FILTER DATE
        # =========================
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
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'LGS' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS lgso,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'MGS' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS mgso,
                COALESCE(ROUND(SUM(CASE WHEN ore_class = 'HGS' THEN tonnage ELSE 0 END)::NUMERIC, 2), 0) AS hgso
            FROM view_geology_ore_production
            {filter_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            chart_data = cursor.fetchone()

        y_data = [float(val or 0) for val in chart_data] if chart_data else [0, 0, 0]

        return JsonResponse({
            "labels": ["LGSO", "MGSO", "HGSO"],
            "y_data": y_data,
        })

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Internal server error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({"error": str(e)}, status=500)
