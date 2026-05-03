# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
from datetime import datetime, date, timedelta
from analytics.services.iup_filter import build_iup_clause
import calendar
logger = logging.getLogger(__name__) 

def parse_iso_week(week_str: str):
    try:
        year_str, week_str = week_str.split("-")
        year = int(year_str)
        week = int(week_str)

        if week < 1 or week > 53:
            raise ValueError("Week must be between 1 and 53")

        return year, week
    except Exception:
        raise ValueError(f"Invalid ISO week format: {week_str}")

def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

# For Chart
def get_chart_fuel(request):
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

    elif filter_type == 'weekly' and filter_week:
        return get_weekly_chart(filter_week, iup_filter)

    elif filter_type == 'all':
        return get_all_chart(iup_filter)

    else:
        return JsonResponse({'error': 'Invalid filter'}, status=400)

def get_daily_chart(filter_date, iup_filter=None):
    where_date = "mf.date_production = %s::date"

    date_params = [filter_date]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND mf.iup_id IN ({placeholders})"
            date_params += iup_ids

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
                        LPAD(charging_time::text, 2, '0') AS charging_time,
                        SUM(volume) AS total_volume
                    FROM mining_fuel_consumption mf
                    WHERE mf.date = {where_date}
                    GROUP BY LPAD(t_load::text, 2, '0')
                )
                SELECT
                    hs.hour_label AS id,
                    hs.left_time,
                    COALESCE(a.total_volume, 0)::numeric(10,2) AS total
                FROM hour_series hs
                LEFT JOIN agg_data a ON hs.left_time = a.t_load_time
                ORDER BY hs.sort_order;
            """


        params = date_params

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()

        df = pd.DataFrame(data, columns=['time', 'left_time', 'total'])
        df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
        # grand total
        grand_total = round(df['total'].sum(), 2)

        return JsonResponse({
            'x_data'     : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
            'y_data'     : df['total'].tolist(),
            'grand_total': float(grand_total)
        }, safe=False)

def get_monthly_chart(filter_year, filter_month, iup_filter=None):
    # Ambil jumlah hari terakhir dalam bulan
    year = int(filter_year)
    month = int(filter_month)

    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    where_date = "date BETWEEN %s AND %s"

    date_params = [tgl_pertama, tgl_terakhir]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND iup_id IN ({placeholders})"
            date_params += iup_ids

    # params untuk generate_series + actual + plan
    params = [
        tgl_pertama, tgl_terakhir,
        *date_params
    ]

    query = f"""
            WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                actual AS (
                    SELECT
                        date::date AS date,
                        SUM(volume) AS volume
                    FROM mining_fuel_consumption
                    WHERE {where_date}
                    GROUP BY date
                )
            SELECT
                TO_CHAR(tanggal.date, 'DD') AS left_date,
                ROUND(COALESCE(a.volume, 0)::numeric, 2) AS total_volume
            FROM tanggal
            LEFT JOIN actual a ON tanggal.date = a.date
            ORDER BY tanggal.date
        """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['left_date', 'total_volume'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0.0).round(2)

    # grand total
    grand_total = round(df['total_volume'].sum(), 2)

    return JsonResponse({
        'x_data'      : df['left_date'].tolist(),
        'y_data'      : df['total_volume'].astype(float).tolist(),
        'grand_total' : float(grand_total)
    }, safe=False)

def get_weekly_chart(filter_week, iup_filter=None):
    iso_year, iso_week = map(int, filter_week.split('-'))

    start_date = date.fromisocalendar(iso_year, iso_week, 1)
    end_date   = date.fromisocalendar(iso_year, iso_week, 7)

    where_date = "TO_CHAR(date, 'IYYY-IW') = %s"

    date_params = [filter_week]

    # FILTER IUP
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND iup_id IN ({placeholders})"
            date_params += iup_ids

    params = [
        start_date, end_date,
        *date_params
    ]

    query = f"""
        WITH hari AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS tanggal
        ),
        actual AS (
            SELECT
                DATE(date) AS tanggal,
                TO_CHAR(date, 'FMDy') AS nama_hari,
                SUM(volume) AS volume
            FROM mining_fuel_consumption
            WHERE {where_date}
            GROUP BY DATE(date), TO_CHAR(date, 'FMDy')
        )
        SELECT
            TO_CHAR(hari.tanggal, 'YYYY-MM-DD') AS tanggal,
            TO_CHAR(hari.tanggal, 'FMDy') AS hari,
            ROUND(COALESCE(a.volume, 0)::numeric, 2) AS total_volume
        FROM hari
        LEFT JOIN actual a ON hari.tanggal = a.tanggal
        ORDER BY hari.tanggal
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['tanggal', 'hari','total_volume'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0.0).round(2)

    # grand total
    grand_total = round(df['total_volume'].sum(), 2)

    return JsonResponse({
        'x_data'     : df['hari'].tolist(),
        'y_data'     : df['total_volume'].astype(float).tolist(),
        'grand_total': float(grand_total)
    }, safe=False)

def get_range_chart(date_start, date_end, iup_filter=None):
    where_date = "date BETWEEN %s AND %s"

    date_params = [date_start, date_end]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND iup_id IN ({placeholders})"
            date_params += iup_ids

    params = [
        date_start, date_end,
        *date_params
    ]

    query = f"""
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
        ),
        actual AS (
            SELECT
                DATE(date) AS tanggal,
                SUM(volume) AS volume
            FROM mining_fuel_consumption
            WHERE {where_date}
            GROUP BY DATE(date)
        )
        SELECT
            TO_CHAR(tanggal.date, 'YYYY-MM-DD') AS tanggal,
            ROUND(COALESCE(a.volume, 0)::numeric, 2) AS total_volume
        FROM tanggal
        LEFT JOIN actual a ON tanggal.date = a.tanggal
        ORDER BY tanggal.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['tanggal','total_volume'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0.0).round(2)

    # grand total
    grand_total = round(df['total_volume'].sum(), 2)

    return JsonResponse({
        'x_data'     : df['tanggal'].tolist(),
        'y_data'     : df['total_volume'].astype(float).tolist(),
        'grand_total': float(grand_total)
    }, safe=False)

def get_yearly_chart(yearly,iup_filter=None):
    where_date = "EXTRACT(YEAR FROM date) = %s"

    date_params = [yearly]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND iup_id IN ({placeholders})"
            date_params += iup_ids

    params = [
        f"{yearly}-01-01",
        *date_params
    ]

    query = f"""
         WITH bulan AS (
            SELECT TO_CHAR(DATE_TRUNC('month', (DATE %s + (n || ' month')::interval)), 'YYYY-MM') AS bulan
            FROM generate_series(0, 11) AS n
        ),
        actual AS (
            SELECT
                TO_CHAR(date, 'YYYY-MM') AS bulan,
                SUM(volume) AS volume
            FROM mining_fuel_consumption
            WHERE {where_date}
            GROUP BY TO_CHAR(date, 'YYYY-MM')
        )
        SELECT
            b.bulan,
            ROUND(COALESCE(a.volume, 0)::numeric, 2) AS total_volume
        FROM bulan b
        LEFT JOIN actual a ON a.bulan = b.bulan
        ORDER BY b.bulan
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['bulan','total_volume'])
    
    # Konversi ke float, pastikan tidak dalam string
    df['total_volume'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0.0).round(2)

    # grand total
    grand_total = round(df['total_volume'].sum(), 2)

    # Define month names
    x_data = df['bulan'].apply(lambda x: datetime.strptime(x, '%Y-%m').strftime('%b %y')).tolist()

    return JsonResponse({
        'x_data'     : x_data,
        'y_data'     : df['total_volume'].astype(float).tolist(),
        'grand_total': float(grand_total)
    }, safe=False)

def get_all_chart(iup_filter=None):
    where_date = "1=1"
    date_params = []

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_date += f" AND iup_id IN ({placeholders})"
            date_params += iup_ids

    query = f""" 
        WITH actual_per_year AS (
            SELECT 
                TO_CHAR(date, 'YYYY') AS tahun,
                SUM(volume) AS total_volume
            FROM mining_fuel_consumption
            WHERE {where_date}
            GROUP BY TO_CHAR(date, 'YYYY')
        )
        SELECT 
            a.tahun AS tahun,
            COALESCE(a.total_volume, 0) AS total_volume
        FROM actual_per_year a
        ORDER BY a.tahun
    """

    params = date_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['tahun', 'total_volume'])
    df['total'] = pd.to_numeric(df['total_volume'], errors='coerce').fillna(0.0).round(2)

    grand_total = round(df['total'].sum(), 2)

    return JsonResponse({
        'x_data': df['tahun'].tolist(),
        'y_data': df['total'].tolist(),
        'grand_total': float(grand_total)
    }, safe=False)

# grouped by fuel_category
def build_fuel_category_filter_clause(
    filter_type=None,
    year=None,
    month=None,
    week=None,
    date_val=None,
    date_start=None,
    date_end=None,
    iup_filter=None,
    alias="f",
):
    today = date.today()

    where_clause = "1=1"
    params = []

    iup_clause, iup_params = build_iup_clause(iup_filter, alias)
    where_clause += iup_clause
    params += iup_params

    date_col = f"{alias}.date"

    if filter_type == "daily" and date_val:
        where_clause += f" AND DATE({date_col}) = %s"
        params.append(date_val)

    elif filter_type == "weekly" and week:
        where_clause += f" AND TO_CHAR({date_col}, 'IYYY-IW') = %s"
        params.append(week)

    elif filter_type == "wtd" and week:
        iso_year, iso_week = parse_iso_week(week)

        start_of_week = date.fromisocalendar(iso_year, iso_week, 1)
        end_of_week = start_of_week + timedelta(days=6)
        end_of_wtd = min(today, end_of_week)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_week, end_of_wtd]

    elif filter_type == "monthly" and year and month:
        where_clause += f"""
            AND EXTRACT(YEAR FROM {date_col}) = %s
            AND EXTRACT(MONTH FROM {date_col}) = %s
        """
        params += [year, month]

    elif filter_type == "mtd" and year and month:
        start_of_month = date(int(year), int(month), 1)
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_of_month = date(int(year), int(month), last_day)
        end_of_mtd = min(today, end_of_month)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_month, end_of_mtd]

    elif filter_type == "yearly" and year:
        where_clause += f" AND EXTRACT(YEAR FROM {date_col}) = %s"
        params.append(year)

    elif filter_type == "ytd" and year:
        start_of_year = date(int(year), 1, 1)
        end_of_year = date(int(year), 12, 31)
        end_of_ytd = min(today, end_of_year)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_year, end_of_ytd]

    elif filter_type == "range" and date_start and date_end:
        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [date_start, date_end]

    return where_clause, params


def get_chart_fuel_category(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")

        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        date_val = request.GET.get("filter_date") or request.GET.get("date")

        where_clause, params = build_fuel_category_filter_clause(
            filter_type=filter_type,
            year=year,
            month=month,
            week=week,
            date_val=date_val,
            date_start=date_start,
            date_end=date_end,
            iup_filter=iup_filter,
            alias="f",
        )

        query = f"""
            SELECT
                COALESCE(NULLIF(TRIM(f.category), ''), 'Unknown') AS category,
                COALESCE(ROUND(SUM(f.volume)::NUMERIC, 2), 0) AS total_volume
            FROM view_mining_fuel_consumption f
            WHERE {where_clause}
            GROUP BY COALESCE(NULLIF(TRIM(f.category), ''), 'Unknown')
            ORDER BY category;
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        grand_total = sum(float(row[1] or 0) for row in rows)

        summary = []
        labels = []
        y_data = []

        for category, total_volume in rows:
            total_volume = float(total_volume or 0)
            percentage = round((total_volume / grand_total) * 100, 2) if grand_total > 0 else 0

            labels.append(category)
            y_data.append(total_volume)

            summary.append({
                "category": category,
                "tonnage": total_volume,   # supaya FE donut tadi langsung jalan
                "volume": total_volume,
                "percentage": percentage,
            })

        return JsonResponse({
            "filter": {
                "filter_type": filter_type,
                "year": year,
                "month": month,
                "week": week,
                "date": date_val,
                "date_start": date_start,
                "date_end": date_end,
                "iup_id": iup_filter,
            },
            "summary": summary,
            "labels": labels,
            "y_data": y_data,
            "grand_total_volume": round(grand_total, 2),
        })

    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({"error": str(e)}, status=500)
    
# by vendors
def get_chart_fuel_vendors(request):
    try:
        filter_type = request.GET.get('filter_type')
        year = request.GET.get('year')
        month = request.GET.get('month')
        week = request.GET.get('week')
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')
        filter_date= request.GET.get('filter_date')

        filter_sql = "WHERE 1=1"
        params = []

        # Tentukan kondisi filter SQL dan parameter
        if filter_type =='daily' and filter_date:
            filter_sql += " AND date = %s"
            params = [filter_date]

        elif filter_type =='range' and date_start and date_end:  # Range
            filter_sql += " AND date BETWEEN %s AND %s"
            params = [date_start, date_end]

        elif filter_type =='weekly' and year and month and week:  # Weekly
            try:
                # Deteksi jika 'week' dalam format ISO (contoh: '2025-03')
                if '-' in str(week):
                    year_str, week_str = str(week).split('-')
                    year = int(year_str)
                    week = int(week_str)

                    # Hitung awal minggu (ISO): Senin minggu ke-X
                    start_date = datetime.strptime(f'{year}-W{week:02}-1', "%G-W%V-%u")
                    end_date = start_date + timedelta(days=6)
                    print("Start:", start_date, "End:", end_date)

                else:
                    # Parsing normal year, month, week
                    year  = int(year)
                    month = int(month)
                    week  = int(week)

                    if not (1 <= month <= 12):
                        return JsonResponse({"error": "Bulan tidak valid (1–12)"}, status=400)
                    if not (1 <= week <= 5):
                        return JsonResponse({"error": "Minggu tidak valid (1–5)"}, status=400)

                    first_day = datetime(year, month, 1)
                    start_date = first_day + timedelta(days=(week - 1) * 7)
                    end_date = start_date + timedelta(days=6)

                    # Koreksi akhir bulan
                    if end_date.month != month:
                        next_month = datetime(year, month, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

            except Exception as e:
                return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)
            
            # Tambahkan WHERE clause filter mingguan
            filter_sql += " AND date BETWEEN %s AND %s"
            params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]

        elif filter_type =='monthly' and year and month:  # Monthly
            filter_sql += " AND EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s" 
            params = [year, month]

        elif filter_type =='yearly' and year:  # Yearly
            filter_sql += " AND EXTRACT(YEAR FROM date) = %s" 
            params = [year]

        elif filter_type =='all':  # All
            pass  # Tidak ada tambahan filter

        else:
            return JsonResponse({'error': 'Invalid or incomplete filter parameters'}, status=400)

        # Query berdasarkan vendor
        query = f"""
                SELECT
                    COALESCE(TRIM(BOTH FROM code), 'Unknown'::text) AS vendors,
                    COALESCE(ROUND(SUM(volume)::NUMERIC, 2), 0) AS total_voume               
                FROM daily_fuel_consumption
                {filter_sql}
                GROUP BY code
                ORDER BY code
            """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # Konversi hasil menjadi list
        labels = [row[0] for row in rows]
        y_data = [float(row[1]) for row in rows]

        return JsonResponse({
            'x_data': labels,
            'y_data': y_data,
        })


    except Exception as e:
        logger.exception("Unexpected error occurred.")
        return JsonResponse({'error': str(e)}, status=500)
