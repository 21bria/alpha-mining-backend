# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from django.utils.timezone import now
logger = logging.getLogger(__name__) 

def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

# For Chart
def get_detail_top_soil(request):
    iup_filter   = request.GET.get("iup_id")
    filter_type  = request.GET.get("filter_type")
    filter_year  = int(request.GET.get("year", 0))
    filter_month = int(request.GET.get("month", 0))
    filter_week  = request.GET.get("week")
    filter_date  = request.GET.get("filter_date")
    date_start   = request.GET.get("date_start")
    date_end     = request.GET.get("date_end")

    if filter_type == "monthly" and filter_year and filter_month:
        return get_detail_monthly(filter_year, filter_month, iup_filter)

    elif filter_type == "daily" and filter_date:
        return get_detail_daily(filter_date, iup_filter)

    elif filter_type == "range" and date_start and date_end:
        return get_detail_range(date_start, date_end, iup_filter)

    elif filter_type == "yearly" and filter_year:
        return get_detail_yearly(filter_year, iup_filter)

    elif filter_type == "weekly" and filter_week:
        return get_detail_weekly(filter_week, iup_filter)

    elif filter_type == "all":
        return get_detail_all(iup_filter)

    else:
        return JsonResponse({"error": "Invalid filter"}, status=400)

def get_detail_daily(filter_date,iup_filter=None):
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
                    SUM(CASE WHEN nama_material IN ('Top Soil') THEN tonnage ELSE 0 END)::numeric AS total_tonnage
                FROM view_mining_productions mp
                WHERE {where_actual}
                GROUP BY LPAD(t_load::text, 2, '0')
            ),
            plan_per_hour AS (
                SELECT
                    ROUND(SUM(COALESCE(topsoil,0))::numeric / 22, 3) AS plan_data
                FROM mining_plan_productions
                WHERE {where_plan}
            )
            SELECT
                hs.hour_label AS id,
                hs.left_time,
                COALESCE(agg.total_tonnage, 0) AS total,
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

    df = pd.DataFrame(data, columns=['id', 'left_time', 'total', 'plan_data'])
    df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    # === Grand Total per tanggal ===
    grand_total = {
        'total' : round(df['total'].sum(), 2),
        'plan'  : round(df['plan_data'].sum(), 2),  # sum dulu, baru round
        'achievement' : round((df['total'].sum() / df['plan_data'].sum() * 100), 2) if df['plan_data'].sum() > 0 else 0.0,
        'avg': round(df['total'].mean(), 2)
    }

    return JsonResponse({
        'x_data'        : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
        'total_actual'  : df['total'].tolist(),
        'total_plan'    : df['plan_data'].tolist(),
        'achievement'   : df['achievement'].tolist(),
        'grand_total'   : grand_total,
    }, safe=False)

def get_detail_monthly(filter_year, filter_month,iup_filter=None):
    year = int(filter_year)
    month = int(filter_month)
    # Ambil jumlah hari terakhir dalam bulan
    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [tgl_pertama, tgl_terakhir]
    plan_params = [tgl_pertama, tgl_terakhir]

    
    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    # params untuk generate_series + actual + plan
    params = [
        tgl_pertama, tgl_terakhir,
        *actual_params,
        *plan_params,
    ]

    query = f"""
    WITH day_series AS (
        SELECT generate_series(%s::date,%s::date,interval '1 day')::date AS left_date
    ),
    actual AS (
        SELECT 
            DATE(date_production) AS prod_date,
            SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS total_tonnage
        FROM view_mining_productions
        WHERE {where_actual}
        GROUP BY DATE(date_production)
    ),
    plan AS (
        SELECT
            DATE(date_plan) AS plan_date,
            SUM(COALESCE(topsoil,0))::numeric AS total_plan
        FROM mining_plan_productions
        WHERE {where_plan}
        GROUP BY DATE(date_plan)
    )
    SELECT
        EXTRACT(DAY FROM ds.left_date)::int AS day,
        ROUND(COALESCE(a.total_tonnage, 0), 2) AS total_tonnage,
        ROUND(COALESCE(p.total_plan, 0), 2)   AS total_plan
    FROM day_series ds
    LEFT JOIN actual a ON ds.left_date = a.prod_date
    LEFT JOIN plan p   ON ds.left_date = p.plan_date
    ORDER BY ds.left_date;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['day', 'total_tonnage', 'total_plan'])

    # pastikan numeric
    for col in ['total_tonnage', 'total_plan']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).round(2)

    # achievement per hari
    df['achievement'] = df.apply(
        lambda r: round((r['total_tonnage'] / r['total_plan'] * 100), 2) if r['total_plan'] > 0 else 0.0,
        axis=1
    )

    # === Grand Total ===
    total_sum = df['total_tonnage'].sum()
    plan_sum  = df['total_plan'].sum()

    grand_total = {
        'total'       : round(total_sum, 2),
        'plan'        : round(plan_sum, 2),
        'achievement' : round((total_sum / plan_sum * 100), 2) if plan_sum > 0 else 0.0,
        'avg_per_day' : round(df['total_tonnage'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    return JsonResponse({
        'x_data'       : df['day'].astype(int).tolist(),   # 1,2,3,..31
        'total_actual' : df['total_tonnage'].astype(float).tolist(),
        'total_plan'   : df['total_plan'].astype(float).tolist(),
        'achievement'  : df['achievement'].astype(float).tolist(),
        'grand_total'  : grand_total
    }, safe=False)

def get_detail_weekly(filter_week,iup_filter=None):
    # iso_week_str = f"{iso_year}-{str(iso_week).zfill(2)}"  # pastikan format IYYY-IW: "2025-04"
    iso_year, iso_week = map(int, filter_week.split('-'))

    start_date = date.fromisocalendar(iso_year, iso_week, 1)
    end_date   = date.fromisocalendar(iso_year, iso_week, 7)

    where_actual = "TO_CHAR(date_production, 'IYYY-IW') = %s"
    where_plan   = "TO_CHAR(date_plan, 'IYYY-IW') = %s"

    actual_params = [filter_week]
    plan_params   = [filter_week]

    # FILTER IUP
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders  = ",".join(["%s"] * len(iup_ids))
            where_actual  += f" AND iup_id IN ({placeholders})"
            where_plan    += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params   += iup_ids

    params = actual_params + plan_params

    query = f"""
        WITH actual AS (
            SELECT
                DATE(date_production) AS tanggal,
                TO_CHAR(date_production, 'FMDy') AS nama_hari,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY tanggal
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,
                TO_CHAR(date_plan, 'FMDy') AS nama_hari,
                SUM(topsoil)::numeric AS topsoil_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY tanggal
        )
        SELECT
            COALESCE(a.tanggal, p.tanggal) AS tanggal,
            COALESCE(a.nama_hari, p.nama_hari) AS hari,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach
        FROM actual a
        FULL OUTER JOIN plan p ON a.tanggal = p.tanggal
        ORDER BY tanggal;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = ['tanggal', 'hari', 'topsoil', 'topsoil_plan', 'topsoil_ach']
    df = pd.DataFrame(data, columns=columns)

    # konversi numeric
    for col in ['topsoil', 'topsoil_plan']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    # total & achievement per hari
    df['total_actual'] = df['topsoil']
    df['total_plan']   = df['topsoil_plan']
    df['achievement']  = df.apply(
        lambda r: round((r['total_actual'] / r['total_plan'] * 100), 2) if r['total_plan'] > 0 else 0.0,
        axis=1
    )

    # === Grand Total Mingguan ===
    total_sum = df['total_actual'].sum()
    plan_sum  = df['total_plan'].sum()

    grand_total = {
        'total'       : round(total_sum, 2),
        'plan'        : round(plan_sum, 2),
        'achievement' : round((total_sum / plan_sum * 100), 2) if plan_sum > 0 else 0.0,
        'avg_per_day' : round(df['total_actual'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    return JsonResponse({
        'x_data'       : df['hari'].astype(str).tolist(),
        'total_actual' : df['total_actual'].astype(float).tolist(),
        'total_plan'   : df['total_plan'].astype(float).tolist(),
        'achievement'  : df['achievement'].astype(float).tolist(),
        'grand_total'  : grand_total
    }, safe=False)

def get_detail_range(date_start, date_end,iup_filter=None):
    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [date_start, date_end]
    plan_params = [date_start, date_end]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    # actual_params = []
    # plan_params   = []

    # # wajib
    # actual_params += [date_start, date_end]
    # plan_params   += [date_start, date_end]

    params = actual_params + plan_params

    query = f"""
        WITH actual AS (
            SELECT
                DATE(date_production) AS tanggal,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY tanggal
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,
                SUM(topsoil)::numeric AS topsoil_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY tanggal
        )
        SELECT
            COALESCE(a.tanggal, p.tanggal) AS tanggal,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach
        FROM actual a
        FULL OUTER JOIN plan p ON a.tanggal = p.tanggal
        ORDER BY tanggal;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()


    columns = ['tanggal', 'topsoil', 'topsoil_plan', 'topsoil_ach']
    df = pd.DataFrame(data, columns=columns)

    # konversi numeric
    for col in ['topsoil', 'topsoil_plan']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    # total per hari
    df['total_actual'] = df['topsoil']
    df['total_plan']   = df['topsoil_plan']
    df['achievement']  = df.apply(
        lambda r: round((r['total_actual'] / r['total_plan'] * 100), 2) if r['total_plan'] > 0 else 0.0,
        axis=1
    )

    # === Grand Total range ===
    total_sum = df['total_actual'].sum()
    plan_sum  = df['total_plan'].sum()

    grand_total = {
        'total'       : round(total_sum, 2),
        'plan'        : round(plan_sum, 2),
        'achievement' : round((total_sum / plan_sum * 100), 2) if plan_sum > 0 else 0.0,
        'avg_per_day' : round(df['total_actual'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    return JsonResponse({
        'x_data'       : df['tanggal'].astype(str).tolist(),
        'total_actual' : df['total_actual'].astype(float).tolist(),
        'total_plan'   : df['total_plan'].astype(float).tolist(),
        'achievement'  : df['achievement'].astype(float).tolist(),
        'grand_total'  : grand_total
    }, safe=False)

def get_detail_yearly(yearly,iup_filter=None):
    where_actual = "EXTRACT(YEAR FROM date_production) = %s"
    where_plan = "EXTRACT(YEAR FROM date_plan) = %s"

    actual_params = [yearly]
    plan_params = [yearly]

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    params = actual_params + plan_params

    query = f"""
        WITH actual AS (
            SELECT
                TO_CHAR(date_production, 'YYYY-MM') AS bulan,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY bulan
        ),
        plan AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY-MM') AS bulan,
                SUM(topsoil)::numeric AS topsoil_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY bulan
        )
        SELECT
            COALESCE(a.bulan, p.bulan) AS bulan,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach
        FROM actual a
        FULL OUTER JOIN plan p ON a.bulan = p.bulan
        ORDER BY bulan;
    """


    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = ['bulan', 'topsoil', 'topsoil_plan', 'topsoil_ach']
    df = pd.DataFrame(data, columns=columns)

    # Konversi kolom ke numeric
    for col in ['topsoil', 'topsoil_plan']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    # total per bulan
    df['total_actual'] = df['topsoil']
    df['total_plan']   = df['topsoil_plan']
    df['achievement']  = df.apply(
        lambda r: round((r['total_actual'] / r['total_plan'] * 100), 2) if r['total_plan'] > 0 else 0.0,
        axis=1
    )

    # Format bulan → Jan 25, Feb 25, dst
    x_data = df['bulan'].apply(lambda x: datetime.strptime(x, '%Y-%m').strftime('%b %y')).tolist()

    # === Grand Total tahunan ===
    total_sum = df['total_actual'].sum()
    plan_sum  = df['total_plan'].sum()

    grand_total = {
        'total'       : round(total_sum, 2),
        'plan'        : round(plan_sum, 2),
        'achievement' : round((total_sum / plan_sum * 100), 2) if plan_sum > 0 else 0.0,
        'avg_per_month': round(df['total_actual'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    return JsonResponse({
        'x_data'       : x_data,  # ['Jan 25', 'Feb 25', ...]
        'total_actual' : df['total_actual'].astype(float).tolist(),
        'total_plan'   : df['total_plan'].astype(float).tolist(),
        'achievement'  : df['achievement'].astype(float).tolist(),
        'grand_total'  : grand_total
    }, safe=False)

def get_detail_all(iup_filter=None):
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    # filter iup
    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f""" 
        WITH actual_per_year AS (
            SELECT 
                TO_CHAR(date_production, 'YYYY') AS tahun,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY TO_CHAR(date_production, 'YYYY')
        ),
        plan_per_year AS (
            SELECT 
                TO_CHAR(date_plan, 'YYYY') AS tahun,
                 SUM(topsoil)::numeric AS topsoil_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY TO_CHAR(date_plan, 'YYYY')
        )
        SELECT 
            COALESCE(a.tahun, p.tahun) AS tahun,
            COALESCE(a.topsoil, 0) AS total,
            COALESCE(p.topsoil_plan, 0) AS plan_data
        FROM actual_per_year a
        FULL OUTER JOIN plan_per_year p ON a.tahun = p.tahun
        ORDER BY tahun
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['tahun','total', 'plan_data'])
    df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
    df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0).round(2)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    return JsonResponse({
        'x_data'      : df['tahun'].tolist(), 
        'total_actual': df['total'].tolist(),
        'total_plan'  : df['plan_data'].tolist(),
        'achievement' : df['achievement'].tolist(),
    }, safe=False)





