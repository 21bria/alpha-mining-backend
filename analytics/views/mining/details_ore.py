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
def get_detail_ore(request):
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

def get_detail_monthly(filter_year, filter_month, iup_filter=None):
    year = int(filter_year)
    month = int(filter_month)

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
            actual_params.extend(iup_ids)
            plan_params.extend(iup_ids)

    query = f"""
        WITH day_series AS (
            SELECT generate_series(
                %s::date,
                %s::date,
                interval '1 day'
            )::date AS left_date
        ),
        agg_data AS (
            SELECT 
                DATE(date_production) AS prod_date,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material IN ('LGLO','MGLO','HGLO','MWS','LGSO','MGSO','HGSO') THEN tonnage ELSE 0 END)::numeric AS ore,
                SUM(CASE WHEN nama_material IN ('LIM','SAP') THEN tonnage ELSE 0 END)::numeric AS total
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY DATE(date_production)
        ),
        plan_data AS (
            SELECT
                DATE(date_plan) AS plan_date,
                SUM(COALESCE(lim,0))::numeric AS plan_lim,
                SUM(COALESCE(sap,0))::numeric AS plan_sap,
                SUM(COALESCE(lim,0) + COALESCE(sap,0))::numeric AS plan_total
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY DATE(date_plan)
        )
        SELECT
            EXTRACT(DAY FROM ds.left_date)::int AS id,
            COALESCE(agg.lim,0) AS lim,
            COALESCE(agg.sap,0) AS sap,
            COALESCE(agg.total,0) AS total,
            COALESCE(pl.plan_total,0) AS plan_data
        FROM day_series ds
        LEFT JOIN agg_data agg ON ds.left_date = agg.prod_date
        LEFT JOIN plan_data pl ON ds.left_date = pl.plan_date
        ORDER BY ds.left_date
    """

    params = [
        tgl_pertama, tgl_terakhir,   # untuk day_series
        *actual_params,             # untuk actual
        *plan_params,               # untuk plan
    ]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['id', 'lim', 'sap', 'total', 'plan_data'])

    for col in ['lim', 'sap', 'total', 'plan_data']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    df['achievement'] = df.apply(
        lambda r: round((r['total'] / r['plan_data'] * 100), 2) if r['plan_data'] > 0 else 0.0,
        axis=1
    )

    total_sum = df['total'].sum()
    plan_sum = df['plan_data'].sum()

    grand_total = {
        'lim': round(df['lim'].sum(), 2),
        'sap': round(df['sap'].sum(), 2),
        'total': round(df['total'].sum(), 2),
        'plan': round(df['plan_data'].sum(), 2),
        'achievement': round((total_sum / plan_sum * 100), 2) if plan_sum > 0 else 0.0,
        'avg': round(df['total'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    return JsonResponse({
        'x_data': df['id'].tolist(),
        'lim_actual': df['lim'].tolist(),
        'sap_actual': df['sap'].tolist(),
        'total_tonnage': df['total'].tolist(),
        'total_plan': df['plan_data'].tolist(),
        'achievement': df['achievement'].tolist(),
        'grand_total': grand_total,
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
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY tanggal
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,
                TO_CHAR(date_plan, 'FMDy') AS nama_hari,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY tanggal
        )
        SELECT
            COALESCE(a.tanggal, p.tanggal) AS tanggal,
            COALESCE(a.nama_hari, p.nama_hari) AS hari,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(CASE WHEN p.lglo_plan > 0 THEN (a.lglo * 100.0 / p.lglo_plan)::numeric ELSE 0 END, 2) AS lglo_ach,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(CASE WHEN p.mglo_plan > 0 THEN (a.mglo * 100.0 / p.mglo_plan)::numeric ELSE 0 END, 2) AS mglo_ach,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(CASE WHEN p.hglo_plan > 0 THEN (a.hglo * 100.0 / p.hglo_plan)::numeric ELSE 0 END, 2) AS hglo_ach,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(CASE WHEN p.mws_plan > 0 THEN (a.mws * 100.0 / p.mws_plan)::numeric ELSE 0 END, 2) AS mws_ach,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(CASE WHEN p.lgso_plan > 0 THEN (a.lgso * 100.0 / p.lgso_plan)::numeric ELSE 0 END, 2) AS lgso_ach,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(CASE WHEN p.mgso_plan > 0 THEN (a.mgso * 100.0 / p.mgso_plan)::numeric ELSE 0 END, 2) AS mgso_ach,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(CASE WHEN p.hgso_plan > 0 THEN (a.hgso * 100.0 / p.hgso_plan)::numeric ELSE 0 END, 2) AS hgso_ach,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(CASE WHEN p.lim_plan > 0 THEN (a.lim * 100.0 / p.lim_plan)::numeric ELSE 0 END, 2) AS lim_ach,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan,
            ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach
        FROM actual a
        FULL OUTER JOIN plan p ON a.tanggal = p.tanggal
        ORDER BY tanggal;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = [
        'tanggal', 'hari',
        'lglo', 'lglo_plan', 'lglo_ach',
        'mglo', 'mglo_plan', 'mglo_ach',
        'hglo', 'hglo_plan', 'hglo_ach',
        'mws',  'mws_plan',  'mws_ach',
        'lgso', 'lgso_plan', 'lgso_ach',
        'mgso', 'mgso_plan', 'mgso_ach',
        'hgso', 'hgso_plan', 'hgso_ach',
        'lim', 'lim_plan', 'lim_ach',
        'sap', 'sap_plan', 'sap_ach'
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols :
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)

    df['total_actual'] = df['limonite'] + df['saprolite']
    df['total_plan']   = df['limonite_plan'] + df['saprolite_plan']
    df['achievement']  = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    # === Grand Total Mingguan ===
    total_sum       = df['total_actual'].sum()
    total_plan_sum  = df['total_plan'].sum()
    limonite_sum    = df['limonite'].sum()
    limonite_plan   = df['limonite_plan'].sum()
    saprolite_sum   = df['saprolite'].sum()
    saprolite_plan  = df['saprolite_plan'].sum()

    grand_total = {
        'lim'            : round(limonite_sum, 2),
        'limonite_plan'  : round(limonite_plan, 2),
        'limonite_ach'   : round((limonite_sum / limonite_plan * 100), 2) if limonite_plan > 0 else 0.0,
        'saprolite'      : round(saprolite_sum, 2),
        'sap'            : round(saprolite_plan, 2),
        'saprolite_ach'  : round((saprolite_sum / saprolite_plan * 100), 2) if saprolite_plan > 0 else 0.0,
        'total'          : round(total_sum, 2),
        'plan'           : round(total_plan_sum, 2),
        'achievement'    : round((total_sum / total_plan_sum * 100), 2) if total_plan_sum > 0 else 0.0,
        'avg'            : round(df['total_actual'].mean(skipna=True), 2) if not df.empty else 0.0
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

    actual_params = []
    plan_params   = []

    # wajib
    actual_params += [date_start, date_end]
    plan_params   += [date_start, date_end]

    params = actual_params + plan_params

    query = f"""
        WITH actual AS (
            SELECT
                DATE(date_production) AS tanggal,
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY tanggal
        ),
        plan AS (
            SELECT
                DATE(date_plan) AS tanggal,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY tanggal
        )
        SELECT
            COALESCE(a.tanggal, p.tanggal) AS tanggal,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(CASE WHEN p.lglo_plan > 0 THEN (a.lglo * 100.0 / p.lglo_plan)::numeric ELSE 0 END, 2) AS lglo_ach,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(CASE WHEN p.mglo_plan > 0 THEN (a.mglo * 100.0 / p.mglo_plan)::numeric ELSE 0 END, 2) AS mglo_ach,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(CASE WHEN p.hglo_plan > 0 THEN (a.hglo * 100.0 / p.hglo_plan)::numeric ELSE 0 END, 2) AS hglo_ach,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(CASE WHEN p.mws_plan > 0 THEN (a.mws * 100.0 / p.mws_plan)::numeric ELSE 0 END, 2) AS mws_ach,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(CASE WHEN p.lgso_plan > 0 THEN (a.lgso * 100.0 / p.lgso_plan)::numeric ELSE 0 END, 2) AS lgso_ach,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(CASE WHEN p.mgso_plan > 0 THEN (a.mgso * 100.0 / p.mgso_plan)::numeric ELSE 0 END, 2) AS mgso_ach,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(CASE WHEN p.hgso_plan > 0 THEN (a.hgso * 100.0 / p.hgso_plan)::numeric ELSE 0 END, 2) AS hgso_ach,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(CASE WHEN p.lim_plan > 0 THEN (a.lim * 100.0 / p.lim_plan)::numeric ELSE 0 END, 2) AS lim_ach,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan,
            ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach
        FROM actual a
        FULL OUTER JOIN plan p ON a.tanggal = p.tanggal
        ORDER BY tanggal;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = [
        'tanggal',
        'lglo', 'lglo_plan', 'lglo_ach',
        'mglo', 'mglo_plan', 'mglo_ach',
        'hglo', 'hglo_plan', 'hglo_ach',
        'mws',  'mws_plan',  'mws_ach',
        'lgso', 'lgso_plan', 'lgso_ach',
        'mgso', 'mgso_plan', 'mgso_ach',
        'hgso', 'hgso_plan', 'hgso_ach',
        'lim', 'lim_plan', 'lim_ach',
        'sap', 'sap_plan', 'sap_ach'
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]


    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)

    df['total_actual'] = df['limonite'] + df['saprolite']
    df['total_plan']   = df['limonite_plan'] + df['saprolite_plan']
    df['achievement']  = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

     # === Grand Total Mingguan ===
    total_sum       = df['total_actual'].sum()
    total_plan_sum  = df['total_plan'].sum()
    limonite_sum    = df['limonite'].sum()
    limonite_plan   = df['limonite_plan'].sum()
    saprolite_sum   = df['saprolite'].sum()
    saprolite_plan  = df['saprolite_plan'].sum()

    grand_total = {
        'lim'            : round(limonite_sum, 2),
        'limonite_plan'  : round(limonite_plan, 2),
        'limonite_ach'   : round((limonite_sum / limonite_plan * 100), 2) if limonite_plan > 0 else 0.0,
        'saprolite'      : round(saprolite_sum, 2),
        'sap'            : round(saprolite_plan, 2),
        'saprolite_ach'  : round((saprolite_sum / saprolite_plan * 100), 2) if saprolite_plan > 0 else 0.0,
        'total'          : round(total_sum, 2),
        'plan'           : round(total_plan_sum, 2),
        'achievement'    : round((total_sum / total_plan_sum * 100), 2) if total_plan_sum > 0 else 0.0,
        'avg'            : round(df['total_actual'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    return JsonResponse({
        'x_data'        : df['tanggal'].astype(str).tolist(),
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
                SUM(CASE WHEN nama_material = 'LGLO' THEN tonnage ELSE 0 END)::numeric AS lglo,
                SUM(CASE WHEN nama_material = 'MGLO' THEN tonnage ELSE 0 END)::numeric AS mglo,
                SUM(CASE WHEN nama_material = 'HGLO' THEN tonnage ELSE 0 END)::numeric AS hglo,
                SUM(CASE WHEN nama_material = 'MWS' THEN tonnage ELSE 0 END)::numeric AS mws,
                SUM(CASE WHEN nama_material = 'LGSO' THEN tonnage ELSE 0 END)::numeric AS lgso,
                SUM(CASE WHEN nama_material = 'MGSO' THEN tonnage ELSE 0 END)::numeric AS mgso,
                SUM(CASE WHEN nama_material = 'HGSO' THEN tonnage ELSE 0 END)::numeric AS hgso,
                SUM(CASE WHEN nama_material = 'LIM' THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY bulan
        ),
        plan AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY-MM') AS bulan,
                SUM(lglo)::numeric AS lglo_plan,
                SUM(mglo)::numeric AS mglo_plan,
                SUM(hglo)::numeric AS hglo_plan,
                SUM(mws)::numeric AS mws_plan,
                SUM(lgso)::numeric AS lgso_plan,
                SUM(mgso)::numeric AS mgso_plan,
                SUM(hgso)::numeric AS hgso_plan,
                SUM(lim)::numeric AS lim_plan,
                SUM(sap)::numeric AS sap_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY bulan
        )
        SELECT
            COALESCE(a.bulan, p.bulan) AS bulan,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(CASE WHEN p.lglo_plan > 0 THEN (a.lglo * 100.0 / p.lglo_plan)::numeric ELSE 0 END, 2) AS lglo_ach,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(CASE WHEN p.mglo_plan > 0 THEN (a.mglo * 100.0 / p.mglo_plan)::numeric ELSE 0 END, 2) AS mglo_ach,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(CASE WHEN p.hglo_plan > 0 THEN (a.hglo * 100.0 / p.hglo_plan)::numeric ELSE 0 END, 2) AS hglo_ach,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(CASE WHEN p.mws_plan > 0 THEN (a.mws * 100.0 / p.mws_plan)::numeric ELSE 0 END, 2) AS mws_ach,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(CASE WHEN p.lgso_plan > 0 THEN (a.lgso * 100.0 / p.lgso_plan)::numeric ELSE 0 END, 2) AS lgso_ach,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(CASE WHEN p.mgso_plan > 0 THEN (a.mgso * 100.0 / p.mgso_plan)::numeric ELSE 0 END, 2) AS mgso_ach,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(CASE WHEN p.hgso_plan > 0 THEN (a.hgso * 100.0 / p.hgso_plan)::numeric ELSE 0 END, 2) AS hgso_ach,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(CASE WHEN p.lim_plan > 0 THEN (a.lim * 100.0 / p.lim_plan)::numeric ELSE 0 END, 2) AS lim_ach,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan,
            ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach
        FROM actual a
        FULL OUTER JOIN plan p ON a.bulan = p.bulan
        ORDER BY bulan;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = [
        'bulan',
        'lglo', 'lglo_plan', 'lglo_ach',
        'mglo', 'mglo_plan', 'mglo_ach',
        'hglo', 'hglo_plan', 'hglo_ach',
        'mws',  'mws_plan',  'mws_ach',
        'lgso', 'lgso_plan', 'lgso_ach',
        'mgso', 'mgso_plan', 'mgso_ach',
        'hgso', 'hgso_plan', 'hgso_ach',
        'lim', 'lim_plan', 'lim_ach',
        'sap', 'sap_plan', 'sap_ach'
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    
    df['total_actual'] = df['limonite'] + df['saprolite']
    df['total_plan']   = df['limonite_plan'] + df['saprolite_plan']
    df['achievement']  = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    # === Grand Total Mingguan ===
    total_sum       = df['total_actual'].sum()
    total_plan_sum  = df['total_plan'].sum()
    limonite_sum    = df['limonite'].sum()
    limonite_plan   = df['limonite_plan'].sum()
    saprolite_sum   = df['saprolite'].sum()
    saprolite_plan  = df['saprolite_plan'].sum()

    grand_total = {
        'lim'            : round(limonite_sum, 2),
        'limonite_plan'  : round(limonite_plan, 2),
        'limonite_ach'   : round((limonite_sum / limonite_plan * 100), 2) if limonite_plan > 0 else 0.0,
        'saprolite'      : round(saprolite_sum, 2),
        'sap'            : round(saprolite_plan, 2),
        'saprolite_ach'  : round((saprolite_sum / saprolite_plan * 100), 2) if saprolite_plan > 0 else 0.0,
        'total'          : round(total_sum, 2),
        'plan'           : round(total_plan_sum, 2),
        'achievement'    : round((total_sum / total_plan_sum * 100), 2) if total_plan_sum > 0 else 0.0,
        'avg'            : round(df['total_actual'].mean(skipna=True), 2) if not df.empty else 0.0
    }

    # Define month names
    x_data = df['bulan'].apply(lambda x: datetime.strptime(x, '%Y-%m').strftime('%b %y')).tolist()


    return JsonResponse({
        'x_data'       : x_data,  # Contoh: ['Jan 25', 'Feb 25', ...]
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
                SUM(CASE WHEN nama_material IN ('LGLO', 'MGLO', 'HGLO', 'LIM') THEN tonnage ELSE 0 END)::numeric AS lim,
                SUM(CASE WHEN nama_material IN ('LGSO', 'MGSO', 'HGSO', 'SAP') THEN tonnage ELSE 0 END)::numeric AS sap
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY TO_CHAR(date_production, 'YYYY')
        ),
        plan_per_year AS (
            SELECT 
                TO_CHAR(date_plan, 'YYYY') AS tahun,
                SUM(
                    COALESCE(lglo, 0) + COALESCE(mglo, 0) + COALESCE(hglo, 0) + COALESCE(lim, 0)
                )::numeric AS lim_plan,
                SUM(
                    COALESCE(lgso, 0) + COALESCE(mgso, 0) + COALESCE(hgso, 0) + COALESCE(sap, 0)
                )::numeric AS sap_plan
            FROM mining_plan_productions
            WHERE {where_plan}
            GROUP BY TO_CHAR(date_plan, 'YYYY')
        )
        SELECT 
            COALESCE(a.tahun, p.tahun) AS tahun,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(
                CASE WHEN COALESCE(p.lim_plan, 0) > 0
                    THEN (COALESCE(a.lim, 0) * 100.0 / p.lim_plan)::numeric
                    ELSE 0
                END, 2
            ) AS lim_ach,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan,
            ROUND(
                CASE WHEN COALESCE(p.sap_plan, 0) > 0
                    THEN (COALESCE(a.sap, 0) * 100.0 / p.sap_plan)::numeric
                    ELSE 0
                END, 2
            ) AS sap_ach
        FROM actual_per_year a
        FULL OUTER JOIN plan_per_year p ON a.tahun = p.tahun
        ORDER BY tahun
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    columns = [
        "tahun",
        "lim", "lim_plan", "lim_ach",
        "sap", "sap_plan", "sap_ach",
    ]

    df = pd.DataFrame(data, columns=columns)

    numeric_cols = ["lim", "lim_plan", "lim_ach", "sap", "sap_plan", "sap_ach"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)

    df["total_actual"] = df["lim"] + df["sap"]
    df["total_plan"] = df["lim_plan"] + df["sap_plan"]
    df["achievement"] = df.apply(
        lambda row: round((row["total_actual"] / row["total_plan"] * 100), 2)
        if row["total_plan"] > 0 else 0,
        axis=1
    )

    # grand total
    total_actual_sum = df["total_actual"].sum()
    total_plan_sum = df["total_plan"].sum()
    lim_sum = df["lim"].sum()
    lim_plan_sum = df["lim_plan"].sum()
    sap_sum = df["sap"].sum()
    sap_plan_sum = df["sap_plan"].sum()

    grand_total = {
        "lim": round(lim_sum, 2),
        "lim_plan": round(lim_plan_sum, 2),
        "lim_achievement": round((lim_sum / lim_plan_sum * 100), 2) if lim_plan_sum > 0 else 0.0,
        "sap": round(sap_sum, 2),
        "sap_plan": round(sap_plan_sum, 2),
        "sap_achievement": round((sap_sum / sap_plan_sum * 100), 2) if sap_plan_sum > 0 else 0.0,
        "total_actual": round(total_actual_sum, 2),
        "total_plan": round(total_plan_sum, 2),
        "achievement": round((total_actual_sum / total_plan_sum * 100), 2) if total_plan_sum > 0 else 0.0,
    }

    return JsonResponse({
        "x_data": df["tahun"].tolist(),
        "total_actual": df["total_actual"].round(1).tolist(),
        "total_plan": df["total_plan"].round(1).tolist(),
        "achievement": df["achievement"].round(1).tolist(),
        "grand_total": grand_total,
    }, safe=False)


