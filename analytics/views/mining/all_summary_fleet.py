# views.py
import logging
from django.http import JsonResponse
from django.db import connections, DatabaseError
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from django.utils.timezone import now
logger = logging.getLogger(__name__) 
from ....utils.db_utils import get_db_vendor

 # Memanggil fungsi utility
db_vendor = get_db_vendor('kqms_db')
import json

def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

def summary_ore(request):
    try:
        if db_vendor == 'postgresql':
            query = """
                SELECT 
                    SUM(CASE WHEN nama_material IN ('LGLO', 'MGLO', 'HGLO','LGSO', 'MGSO', 'HGSO','LIM','SAP') THEN tonnage ELSE 0 END)::numeric  AS total,
                    SUM(CASE WHEN nama_material IN ('LGLO', 'MGLO', 'HGLO','LIM') THEN tonnage ELSE 0 END)::numeric AS limonite,
                    SUM(CASE WHEN nama_material IN ('LGSO', 'MGSO', 'HGSO','SAP') THEN tonnage ELSE 0 END)::numeric AS saprolite
                FROM view_mining_productions
                """
        else:
            raise ValueError("Unsupported database vendor.")  
        # Use the correct database connection
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()

        total_ore = [entry[0] for entry in data]
        data_hpal = [entry[1] for entry in data]
        data_rkef = [entry[2] for entry in data]

        return JsonResponse({
            'data_hpal': data_hpal,
            'data_rkef': data_rkef,
            'total_ore': total_ore,
        })

    except DatabaseError as e:
        logger.error(f"Database query failed: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
      
def summary_mines(request):
    try:
        if db_vendor == 'postgresql':
            query = """
               SELECT 
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "TopSoil",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Waste",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "OB",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Quarry",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Ballast",
                    ROUND(COALESCE(SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END), 0)::numeric, 2) AS "Biomass"
                FROM view_mining_productions
                """
        else:
            raise ValueError("Unsupported database vendor.")  
        # Use the correct database connection
        with connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()

        data_topsoil = [entry[0] for entry in data]
        data_waste   = [entry[1] for entry in data]
        data_ob      = [entry[2] for entry in data]
        data_quarry  = [entry[3] for entry in data]
        data_ballast = [entry[4] for entry in data]
        data_biomass = [entry[5] for entry in data]

        # Tambahkan data_orders: jumlahkan  ob + quarry + ballast + biomass
        data_orders = [entry[2] + entry[3] + entry[4] + entry[5] for entry in data]

        return JsonResponse({
            'data_topsoil'  : data_topsoil,
            'data_waste'    : data_waste,
            'data_ob'       : data_ob,
            'data_ballast'  : data_ballast,
            'data_quarry'   : data_quarry,
            'data_biomass'  : data_biomass,
            'data_orders'   : data_orders,
        })
    except DatabaseError as e:
        logger.error(f"Database query failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)    

def build_filter_clause(filter_type, year, month, week, date_val, date_start, date_end):
    today = date.today()

    where_actual = "1=1"
    where_plan = "1=1"
    params = []

    if filter_type == 'daily' and date_val:
        group_actual = "DATE(date_production)"
        group_plan = "DATE(date_plan)"
        where_actual += " AND DATE(date_production) = %s"
        where_plan += " AND DATE(date_plan) = %s"
        params += [date_val, date_val]

    elif filter_type == 'weekly' and week:
        group_actual = "TO_CHAR(date_production, 'IYYY-IW')"
        group_plan = "TO_CHAR(date_plan, 'IYYY-IW')"
        where_actual += " AND TO_CHAR(date_production, 'IYYY-IW') = %s"
        where_plan += " AND TO_CHAR(date_plan, 'IYYY-IW') = %s"
        params += [week, week]

    elif filter_type == 'wtd' and year and month and week:
        # WTD = dari Senin di minggu itu sampai hari ini ATAU akhir minggu itu
        start_of_week = today - timedelta(days=today.weekday())
        end_of_wtd = today

        # Jika tahun/bulan/minggu spesifik dikirim, kita hitung dari situ
        group_actual = "DATE(date_production)"
        group_plan   = "DATE(date_plan)"

        # Hitung awal minggu dari kombinasi tahun + minggu ISO
        if year and week:
            start_of_week = date.fromisocalendar(int(year), int(week), 1)  # Senin
            end_of_week = start_of_week + timedelta(days=6)
            end_of_wtd = min(today, end_of_week)

        where_actual += " AND date_production BETWEEN %s AND %s"
        where_plan += " AND date_plan BETWEEN %s AND %s"
        params += [start_of_week, end_of_wtd, start_of_week, end_of_wtd]

    elif filter_type == 'monthly' and year and month:
        group_actual = "TO_CHAR(date_production, 'YYYY-MM')"
        group_plan = "TO_CHAR(date_plan, 'YYYY-MM')"
        where_actual += " AND EXTRACT(YEAR FROM date_production) = %s AND EXTRACT(MONTH FROM date_production) = %s"
        where_plan += " AND EXTRACT(YEAR FROM date_plan) = %s AND EXTRACT(MONTH FROM date_plan) = %s"
        params += [year, month, year, month]

    elif filter_type == 'mtd' and year and month:
        start_of_month = date(int(year), int(month), 1)
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_of_month = date(int(year), int(month), last_day)
        end_of_mtd = min(today, end_of_month)

        group_actual = "DATE(date_production)"
        group_plan = "DATE(date_plan)"
        where_actual += " AND date_production BETWEEN %s AND %s"
        where_plan += " AND date_plan BETWEEN %s AND %s"
        params += [start_of_month, end_of_mtd, start_of_month, end_of_mtd]

    elif filter_type == 'yearly' and year:
        group_actual = "EXTRACT(YEAR FROM date_production)::int"
        group_plan = "EXTRACT(YEAR FROM date_plan)::int"
        where_actual += " AND EXTRACT(YEAR FROM date_production) = %s"
        where_plan += " AND EXTRACT(YEAR FROM date_plan) = %s"
        params += [year, year]

    elif filter_type == 'ytd' and year:
        start_of_year = date(int(year), 1, 1)
        end_of_year = date(int(year), 12, 31)
        end_of_ytd = min(today, end_of_year)

        group_actual = "DATE(date_production)"
        group_plan = "DATE(date_plan)"
        where_actual += " AND date_production BETWEEN %s AND %s"
        where_plan += " AND date_plan BETWEEN %s AND %s"
        params += [start_of_year, end_of_ytd, start_of_year, end_of_ytd]

    elif filter_type == 'range' and date_start and date_end:
        group_actual = "DATE(date_production)"
        group_plan = "DATE(date_plan)"
        where_actual += " AND date_production BETWEEN %s AND %s"
        where_plan += " AND date_plan BETWEEN %s AND %s"
        params += [date_start, date_end, date_start, date_end]

    else:  # 'all' atau tidak valid
        group_actual = "EXTRACT(YEAR FROM date_production)::int"
        group_plan = "EXTRACT(YEAR FROM date_plan)::int"

    return where_actual, where_plan, group_actual, group_plan, params

# For Summary plan vc actual
def get_summary_dataframe(where_actual, where_plan, group_actual, group_plan, params):
    query = f"""
        WITH actual AS (
            SELECT
                {group_actual} AS periode,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass,
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
            GROUP BY {group_actual}
        ),
        plan AS (
            SELECT
                {group_plan} AS periode,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan,
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
            GROUP BY {group_plan}
        )
        SELECT
            COALESCE(a.periode, p.periode) AS periode,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(COALESCE(a.ob, 0), 2) AS ob,
            ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
            ROUND(COALESCE(a.waste, 0), 2) AS waste,
            ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
            ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
            ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
            ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
            ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
            ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
            ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
            ROUND(COALESCE(a.lglo, 0), 2) AS lglo,
            ROUND(COALESCE(p.lglo_plan, 0), 2) AS lglo_plan,
            ROUND(COALESCE(a.mglo, 0), 2) AS mglo,
            ROUND(COALESCE(p.mglo_plan, 0), 2) AS mglo_plan,
            ROUND(COALESCE(a.hglo, 0), 2) AS hglo,
            ROUND(COALESCE(p.hglo_plan, 0), 2) AS hglo_plan,
            ROUND(COALESCE(a.mws, 0), 2) AS mws,
            ROUND(COALESCE(p.mws_plan, 0), 2) AS mws_plan,
            ROUND(COALESCE(a.lgso, 0), 2) AS lgso,
            ROUND(COALESCE(p.lgso_plan, 0), 2) AS lgso_plan,
            ROUND(COALESCE(a.mgso, 0), 2) AS mgso,
            ROUND(COALESCE(p.mgso_plan, 0), 2) AS mgso_plan,
            ROUND(COALESCE(a.hgso, 0), 2) AS hgso,
            ROUND(COALESCE(p.hgso_plan, 0), 2) AS hgso_plan,
            ROUND(COALESCE(a.lim, 0), 2) AS lim,
            ROUND(COALESCE(p.lim_plan, 0), 2) AS lim_plan,
            ROUND(COALESCE(a.sap, 0), 2) AS sap,
            ROUND(COALESCE(p.sap_plan, 0), 2) AS sap_plan
        FROM actual a
        FULL OUTER JOIN plan p ON a.periode = p.periode
        ORDER BY periode
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=[
        'periode', 'topsoil', 'topsoil_plan',
        'ob', 'ob_plan', 'waste', 'waste_plan', 'quarry', 'quarry_plan',
        'ballast', 'ballast_plan', 'biomass', 'biomass_plan',
        'lglo', 'lglo_plan', 'mglo', 'mglo_plan', 'hglo', 'hglo_plan',
        'mws', 'mws_plan', 'lgso', 'lgso_plan', 'mgso', 'mgso_plan', 'hgso', 'hgso_plan',
        'lim', 'lim_plan', 'sap', 'sap_plan'
    ])

    return df

def generate_summary(df, label):
    ore_cols = ['lglo', 'mglo', 'hglo', 'lgso', 'mgso', 'hgso', 'mws','lim','sap']
    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso', 'mws','sap']
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']

    ore_plan_cols = [f + '_plan' for f in ore_cols]
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    df['total_ore'] = df[ore_cols].sum(axis=1)
    df['total_ore_plan'] = df[ore_plan_cols].sum(axis=1)
    df['total_limonite'] = df[lim_cols].sum(axis=1)
    df['total_limonite_plan'] = df[lim_plan_cols].sum(axis=1)
    df['total_saprolite'] = df[sap_cols].sum(axis=1)
    df['total_saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['total_non_ore'] = df[non_ore_cols].sum(axis=1)
    df['total_non_ore_plan'] = df[non_ore_plan_cols].sum(axis=1)

    df['total_actual'] = df['total_ore'] + df['total_non_ore']
    df['total_plan'] = df['total_ore_plan'] + df['total_non_ore_plan']

    def safe_div(a, b):
        return round((a / b * 100), 0) if b > 0 else 0

    return {
        'label': label,
        'total_ore': float(round(df['total_ore'].sum(), 2)),
        'total_ore_plan': float(round(df['total_ore_plan'].sum(), 2)),
        'total_limonite': float(round(df['total_limonite'].sum(), 2)),
        'total_limonite_plan': float(round(df['total_limonite_plan'].sum(), 2)),
        'total_saprolite': float(round(df['total_saprolite'].sum(), 2)),
        'total_saprolite_plan': float(round(df['total_saprolite_plan'].sum(), 2)),
        'total_non_ore': float(round(df['total_non_ore'].sum(), 2)),
        'total_non_ore_plan': float(round(df['total_non_ore_plan'].sum(), 2)),
        'total_actual': float(round(df['total_actual'].sum(), 2)),
        'total_plan': float(round(df['total_plan'].sum(), 2)),
        'achievement': float(safe_div(df['total_actual'].sum(), df['total_plan'].sum())),
        'achievement_ore': float(safe_div(df['total_ore'].sum(), df['total_ore_plan'].sum())),
        'achievement_limonite': float(safe_div(df['total_limonite'].sum(), df['total_limonite_plan'].sum())),
        'achievement_saprolite': float(safe_div(df['total_saprolite'].sum(), df['total_saprolite_plan'].sum())),
        'achievement_non_ore': float(safe_div(df['total_non_ore'].sum(), df['total_non_ore_plan'].sum())),
    }

def get_summary_mines(request):
    filter_type  = request.GET.get('filter_type', 'all')
    filter_year  = request.GET.get('filter_year')
    filter_month = request.GET.get('filter_month')
    filter_week  = request.GET.get('filter_week')
    filter_date  = request.GET.get('filter_date')
    date_start   = request.GET.get('date_start')
    date_end     = request.GET.get('date_end')

    if db_vendor != 'postgresql':
        return JsonResponse({'error': 'Unsupported DB'}, status=400)

    result = {}

    if filter_type == 'monthly':
        # === Monthly ===
        wa1, wp1, ga1, gp1, param1 = build_filter_clause('monthly', filter_year, filter_month, None, None, None, None)
        df_monthly = get_summary_dataframe(wa1, wp1, ga1, gp1, param1)
        result['monthly'] = generate_summary(df_monthly, 'MONTHLY')

        # === MTD ===
        wa2, wp2, ga2, gp2, param2 = build_filter_clause('mtd', filter_year, filter_month, None, None, None, None)
        df_mtd = get_summary_dataframe(wa2, wp2, ga2, gp2, param2)
        result['mtd'] = generate_summary(df_mtd, 'MTD')

    elif filter_type == 'weekly':
        # === Weekly ===
        wa1, wp1, ga1, gp1, param1 = build_filter_clause('weekly', filter_year, filter_month, filter_week, None, None, None)
        df_weekly = get_summary_dataframe(wa1, wp1, ga1, gp1, param1)
        result['weekly'] = generate_summary(df_weekly, 'WEEKLY')

        # === WTD ===
        wa2, wp2, ga2, gp2, param2 = build_filter_clause('wtd', filter_year, filter_month, filter_week, None, None, None)
        df_wtd = get_summary_dataframe(wa2, wp2, ga2, gp2, param2)
        result['wtd'] = generate_summary(df_wtd, 'WTD')

    elif filter_type == 'yearly':
        # === Yearly ===
        wa1, wp1, ga1, gp1, param1 = build_filter_clause('yearly', filter_year, None, None, None, None, None)
        df_yearly = get_summary_dataframe(wa1, wp1, ga1, gp1, param1)
        result['yearly'] = generate_summary(df_yearly, 'YEARLY')

        # === YTD ===
        wa2, wp2, ga2, gp2, param2 = build_filter_clause('ytd', filter_year, None, None, None, None, None)
        df_ytd = get_summary_dataframe(wa2, wp2, ga2, gp2, param2)
        result['ytd'] = generate_summary(df_ytd, 'YTD')

    elif filter_type == 'range':
        # === Range (custom date range) ===
        wa, wp, ga, gp, params = build_filter_clause('range', None, None, None, None, date_start, date_end)
        df_range = get_summary_dataframe(wa, wp, ga, gp, params)
        result['range'] = generate_summary(df_range, 'RANGE')
    
    elif filter_type == 'daily':
        # === Daily ===
        wa, wp, ga, gp, params = build_filter_clause('daily', None, None, None, filter_date, None, None)
        df_daily = get_summary_dataframe(wa, wp, ga, gp, params)
        result['daily'] = generate_summary(df_daily, 'DAILY')

    else:
        # === All Data (tanpa filter) ===
        wa, wp, ga, gp, params = build_filter_clause('all', None, None, None, None, None, None)
        df_all = get_summary_dataframe(wa, wp, ga, gp, params)
        result['all'] = generate_summary(df_all, 'ALL')

    return JsonResponse(result, safe=False)

# For Chart
def get_chart_ore_mining(request):
    filter_type  = request.GET.get('filter_type')
    filter_year  = int(request.GET.get('filter_year', 0))
    filter_month = int(request.GET.get('filter_month', 0))
    filter_week  = request.GET.get('filter_week')
    filter_date  = request.GET.get('filter_date')
    date_start   = request.GET.get('date_start')
    date_end     = request.GET.get('date_end')

    if filter_type == 'monthly' and filter_year and filter_month:
        return get_monthly_chart(filter_year, filter_month)
    
    elif filter_type == 'daily' and filter_date:
        return get_daily_chart(filter_date)

    elif filter_type == 'range' and date_start and date_end:
        return get_range_chart(date_start, date_end)

    elif filter_type == 'yearly' and filter_year:
        return get_yearly_chart(filter_year)

    elif filter_type == 'weekly' and filter_week:
        return get_weekly_chart(filter_week)

    elif filter_type == 'all':
        return get_all_chart()

    else:
        return JsonResponse({'error': 'Invalid filter'}, status=400)

def get_daily_chart(filter_date):
        if db_vendor == 'postgresql':
            query = """ 
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
                        -- total produksi aktual tanpa MWS
                    SUM(tonnage) AS total_tonnage
                    FROM view_mining_productions mp
                    WHERE mp.date_production = %s::date
                    GROUP BY LPAD(t_load::text, 2, '0')
                ),
                plan_per_hour AS (
                    SELECT
                        ROUND((
                            SUM(
                                COALESCE(topsoil, 0) + COALESCE(ob, 0) + COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                                COALESCE(hglo, 0) + COALESCE(waste, 0) + COALESCE(mws, 0) + COALESCE(lgso, 0) +
                                COALESCE(mgso, 0) + COALESCE(hgso, 0) + COALESCE(lim, 0) + COALESCE(sap, 0) +  
                                COALESCE(quarry, 0) + COALESCE(ballast, 0) + COALESCE(biomass, 0)
                            ) / 22
                        )::numeric, 2) AS plan_data
                    FROM mining_plan_productions
                    WHERE date_plan = %s::date
                )
                SELECT
                    hs.hour_label AS id,
                    hs.left_time,
                    COALESCE(a.total_tonnage, 0)::numeric(10,2) AS total,
                    p.plan_data
                FROM hour_series hs
                LEFT JOIN agg_data a ON hs.left_time = a.t_load_time
                CROSS JOIN plan_per_hour p
                ORDER BY hs.sort_order;
            """
        else:
            raise ValueError("Unsupported vendor")

        params = [filter_date,filter_date]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()

        df = pd.DataFrame(data, columns=['time', 'left_time', 'total', 'plan_data'])
        df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
        df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0).round(2)
        df['achievement'] = df.apply(lambda r: round((r['total'] / r['plan_data'] * 100), 2) if r['plan_data'] > 0 else 0.0, axis=1)

        return JsonResponse({
            'x_data'    : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
            'total_actual': df['total'].tolist(),
            'total_plan': df['plan_data'].tolist(),
            'achievement': df['achievement'].tolist(),
        }, safe=False)

def get_chart_ore_quality(request):
    filter_type  = request.GET.get('filter_type')
    filter_date  = request.GET.get('filter_date')
    if filter_type == 'daily' and filter_date:
        return get_daily_ore_chart(filter_date)

    else:
        return JsonResponse({'error': 'Invalid filter'}, status=400)
    
def get_daily_ore_chart(filter_date):
        if db_vendor == 'postgresql':
            query = """ 
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
                        TO_CHAR(make_time(t_load::int, 0, 0), 'HH24') AS t_load_time,
                        SUM(
                            COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                            COALESCE(hglo, 0) + COALESCE(mws, 0) +
                            COALESCE(lgso, 0) + COALESCE(mgso, 0) +
                            COALESCE(hgso, 0) + COALESCE(lim, 0) +
                            COALESCE(sap, 0)
                        ) AS plan_data,
                        -- Total tonnage utama (tanpa mws)
                        SUM(
                            COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                            COALESCE(hglo, 0) + COALESCE(lgso, 0) +
                            COALESCE(mgso, 0) + COALESCE(hgso, 0) +
                            COALESCE(lim, 0)  + COALESCE(sap, 0) 
                        ) AS total_tonnage
                    FROM view_mining_productions
                    LEFT JOIN plan_productions 
                        ON mine_productions.date_production = plan_productions.date_plan
                    WHERE date_production = %s
                    GROUP BY t_load
                )
                SELECT
                    hs.hour_label AS id,
                    hs.left_time,  -- ini sekarang berupa string '07', '08', dst.
                    COALESCE(agg.total_tonnage, 0)::numeric(10,2) AS total,
                    ROUND(COALESCE(agg.plan_data, 0)::numeric / 22, 2) AS plan_data
                FROM hour_series hs
                LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
                ORDER BY hs.sort_order;
            """
        elif db_vendor in [ 'mssql', 'microsoft']:
            query = """
                WITH working_hours AS (
                    SELECT 
                        hour_label = v.number,
                        sort_order = CASE WHEN v.number >= 7 THEN v.number ELSE v.number + 24 END
                    FROM master..spt_values v
                    WHERE v.type = 'P' AND v.number BETWEEN 0 AND 23
                ),
                hour_series AS (
                    SELECT 
                        CAST(CAST(hour_label AS VARCHAR) + ':00:00' AS TIME) AS left_time,
                        hour_label,
                        sort_order
                    FROM working_hours
                ),
                agg_data AS (
                    SELECT 
                        CAST(CAST(CAST(t_load AS INT) AS VARCHAR) + ':00:00' AS TIME) AS t_load_time,
                        SUM(ISNULL(lglo, 0) + ISNULL(mglo, 0) + ISNULL(hglo, 0) + ISNULL(lgso, 0) + ISNULL(mgso, 0) + ISNULL(hgso, 0) + ISNULL(lim, 0) + ISNULL(sap, 0)) AS total_tonnage,
                        SUM(ISNULL(lglo, 0) + ISNULL(mglo, 0) + ISNULL(hglo, 0) + ISNULL(mws, 0) + ISNULL(lgso, 0) + ISNULL(mgso, 0) + ISNULL(hgso, 0) + ISNULL(lim, 0) + ISNULL(sap, 0)) AS plan_data
                    FROM view_mining_productions mp
                    LEFT JOIN plan_productions pp ON mp.date_production = pp.date_plan
                    WHERE date_production = %s
                    GROUP BY t_load
                )
                SELECT
                    hs.hour_label AS time,
                    hs.left_time,
                    ISNULL(SUM(agg.total_tonnage), 0) AS total,
                    ROUND(ISNULL(SUM(DISTINCT agg.plan_data), 0) / 22.0, 2) AS plan_data
                FROM hour_series hs
                LEFT JOIN agg_data agg ON hs.left_time = agg.t_load_time
                GROUP BY hs.hour_label, hs.left_time, hs.sort_order
                ORDER BY hs.sort_order
            """
        else:
            raise ValueError("Unsupported vendor")


        params = [filter_date]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()

        df = pd.DataFrame(data, columns=['time', 'left_time', 'total', 'plan_data'])
        df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0.0).round(2)
        df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0).round(2)
        df['achievement'] = df.apply(lambda r: round((r['total'] / r['plan_data'] * 100), 2) if r['plan_data'] > 0 else 0.0, axis=1)

        return JsonResponse({
            'x_data'    : df['left_time'].tolist(),  # ini label jam (misal: "01:00", "02:00", ...)
            'total_actual': df['total'].tolist(),
            'total_plan': df['plan_data'].tolist(),
            'achievement': df['achievement'].tolist(),
        }, safe=False)

# kqms/dashboard/api/summary/mines/ore?filter_type=monthly&filter_year=2025&filter_month=7
def get_monthly_chart(filter_year, filter_month):
    year = int(filter_year)
    month = int(filter_month)

    # Ambil jumlah hari terakhir bulan tsb
    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama  = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    # === PARAMETER ===
    params_main = [
        tgl_pertama, tgl_terakhir,  # generate_series
        tgl_pertama, tgl_terakhir,  # actual
        tgl_pertama, tgl_terakhir   # plan
    ]

    # === QUERY UTAMA: Produksi dan Plan ===
    query_main = """
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
        ),
        actual AS (
            SELECT
                date_production::date AS date,
                SUM(tonnage) AS tonnage
            FROM view_mining_productions
            WHERE date_production BETWEEN %s AND %s
            GROUP BY date_production
        ),
        plan AS (
            SELECT 
                date_plan::date AS date,
                SUM(
                    COALESCE(topsoil, 0) + COALESCE(ob, 0) + COALESCE(lglo, 0) + 
                    COALESCE(mglo, 0) + COALESCE(hglo, 0) + COALESCE(waste, 0) + 
                    COALESCE(mws, 0)  + COALESCE(lgso, 0) + COALESCE(mgso, 0) + 
                    COALESCE(hgso, 0) + COALESCE(lim, 0)  + COALESCE(sap, 0) + 
                    COALESCE(quarry, 0) + COALESCE(ballast, 0) + COALESCE(biomass, 0)
                ) AS plan_data
            FROM mining_plan_productions
            WHERE date_plan BETWEEN %s AND %s
            GROUP BY date_plan
        )
        SELECT
            TO_CHAR(tanggal.date, 'DD') AS left_date,
            ROUND(COALESCE(a.tonnage, 0)::numeric, 2) AS total_tonnage,
            ROUND(COALESCE(p.plan_data, 0)::numeric, 2) AS total_plan
        FROM tanggal
        LEFT JOIN actual a ON tanggal.date = a.date
        LEFT JOIN plan p ON tanggal.date = p.date
        ORDER BY tanggal.date
    """

    with connection.cursor() as cursor:
        cursor.execute(query_main, params_main)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['left_date', 'total_tonnage', 'total_plan'])
    df['total_tonnage'] = pd.to_numeric(df['total_tonnage'], errors='coerce').fillna(0.0)
    df['total_plan'] = pd.to_numeric(df['total_plan'], errors='coerce').fillna(0.0)

    # === QUERY TAMBAHAN: DETAIL FLEET ===
    query_fleet = """
        SELECT
            date_production::date AS date,
            nama_material as material,
            COUNT(DISTINCT hauler) AS hauler_used,
            COUNT(DISTINCT loader) AS excavator_used
        FROM view_mining_productions
        WHERE date_production BETWEEN %s AND %s
        GROUP BY date_production, nama_material
        ORDER BY date_production, nama_material
    """

    with connection.cursor() as cursor:
        cursor.execute(query_fleet, [tgl_pertama, tgl_terakhir])
        fleet_data = cursor.fetchall()

    df_fleet = pd.DataFrame(fleet_data, columns=['date', 'material', 'hauler_used', 'excavator_used'])

    # === HASIL AKHIR ===
    return JsonResponse({
        "x_data": df['left_date'].tolist(),
        "total_tonnage": df['total_tonnage'].astype(float).tolist(),
        "total_plan": df['total_plan'].astype(float).tolist(),
        # Data fleet buat tooltip
        "fleet_detail": df_fleet.to_dict(orient='records')
    }, safe=False)

# kqms/dashboard/api/summary/mines/ore?filter_type=weekly&filter_week=2025-04
def get_weekly_chart(filter_week):
    # iso_week_str = f"{iso_year}-{str(iso_week).zfill(2)}"  # pastikan format IYYY-IW: "2025-04"
      # Misal filter_week = '2025-04'
    iso_year, iso_week = map(int, filter_week.split('-'))

    # Ambil hari pertama dan terakhir dari minggu ISO tersebut
    start_date = date.fromisocalendar(iso_year, iso_week, 1)  # Senin
    end_date   = date.fromisocalendar(iso_year, iso_week, 7)    # Minggu

    params     = [start_date, end_date, filter_week, filter_week]

    query = """
        WITH hari AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS tanggal
        ),
        actual AS (
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
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass
            FROM view_mining_productions
            WHERE TO_CHAR(date_production, 'IYYY-IW') = %s
            GROUP BY DATE(date_production), TO_CHAR(date_production, 'FMDy')
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
                SUM(sap)::numeric AS sap_plan,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan
            FROM mining_plan_productions
            WHERE TO_CHAR(date_plan, 'IYYY-IW') = %s
            GROUP BY DATE(date_plan), TO_CHAR(date_plan, 'FMDy')
        )
        SELECT
            TO_CHAR(hari.tanggal, 'YYYY-MM-DD') AS tanggal,
            TO_CHAR(hari.tanggal, 'FMDy') AS hari,
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
            ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach,
            ROUND(COALESCE(a.ob, 0), 2) AS ob,
            ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
            ROUND(CASE WHEN p.ob_plan > 0 THEN (a.ob * 100.0 / p.ob_plan)::numeric ELSE 0 END, 2) AS ob_ach,
            ROUND(COALESCE(a.waste, 0), 2) AS waste,
            ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
            ROUND(CASE WHEN p.waste_plan > 0 THEN (a.waste * 100.0 / p.waste_plan)::numeric ELSE 0 END, 2) AS waste_ach,
            ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
            ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
            ROUND(CASE WHEN p.quarry_plan > 0 THEN (a.quarry * 100.0 / p.quarry_plan)::numeric ELSE 0 END, 2) AS quarry_ach,
            ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
            ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
            ROUND(CASE WHEN p.ballast_plan > 0 THEN (a.ballast * 100.0 / p.ballast_plan)::numeric ELSE 0 END, 2) AS ballast_ach,
            ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
            ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
            ROUND(CASE WHEN p.biomass_plan > 0 THEN (a.biomass * 100.0 / p.biomass_plan)::numeric ELSE 0 END, 2) AS biomass_ach
        FROM hari
        LEFT JOIN actual a ON hari.tanggal = a.tanggal
        LEFT JOIN plan p ON hari.tanggal = p.tanggal
        ORDER BY hari.tanggal
    """

    # params = [filter_week, filter_week]

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
        'sap', 'sap_plan', 'sap_ach',
        'topsoil', 'topsoil_plan', 'topsoil_ach',
        'ob', 'ob_plan', 'ob_ach',
        'waste', 'waste_plan', 'waste_ach',
        'quarry', 'quarry_plan', 'quarry_ach',
        'ballast', 'ballast_plan', 'ballast_ach',
        'biomass', 'biomass_plan', 'biomass_ach',
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols + non_ore_cols + non_ore_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['non_ore']        = df[non_ore_cols].sum(axis=1)
    df['non_ore_plan']   = df[non_ore_plan_cols].sum(axis=1)
    

    df['total_actual'] = df['limonite'] + df['saprolite'] + df['non_ore'] 
    df['total_plan']   = df['limonite_plan'] + df['saprolite_plan'] +  df['non_ore_plan']
    df['achievement']  = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    df['non_ore_ach']   = df.apply(lambda r: round((r['non_ore'] / r['non_ore_plan'] * 100), 2) if r['non_ore_plan'] > 0 else 0, axis=1)


    return JsonResponse({
        'x_data'        : df['hari'].astype(str).tolist(),
        # 'limonite'      : df['limonite'].tolist(),
        # 'limonite_plan' : df['limonite_plan'].tolist(),
        # 'limonite_ach'  : df['limonite_ach'].tolist(),
        # 'saprolite'     : df['saprolite'].tolist(),
        # 'saprolite_plan': df['saprolite_plan'].tolist(),
        # 'saprolite_ach' : df['saprolite_ach'].tolist(),
        # 'total_actual' : df['total_actual'].astype(float).tolist(),
        # 'total_plan'   : df['total_plan'].astype(float).tolist(),
        # 'achievement'  : df['achievement'].astype(float).tolist(),
        'total_actual' : df['total_actual'].round(1).tolist(),
        'total_plan'   : df['total_plan'].round(1).tolist(),
        'achievement'  : df['achievement'].round(1).tolist(),
    }, safe=False)

# kqms/dashboard/api/summary/mines/ore?filter_type=range&date_start='2025-06-01'&date_end='2025-06-20'
def get_range_chart(date_start, date_end):
    query = """
        WITH tanggal AS (
            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
        ),
        actual AS (
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
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass
            FROM view_mining_productions
            WHERE date_production BETWEEN %s AND %s
            GROUP BY DATE(date_production)
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
                SUM(sap)::numeric AS sap_plan,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan
            FROM mining_plan_productions
            WHERE date_plan BETWEEN %s AND %s
            GROUP BY DATE(date_plan)
        )
        SELECT
            TO_CHAR(tanggal.date, 'YYYY-MM-DD') AS tanggal,
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
            ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach,
            ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
            ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
            ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach,
            ROUND(COALESCE(a.ob, 0), 2) AS ob,
            ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
            ROUND(CASE WHEN p.ob_plan > 0 THEN (a.ob * 100.0 / p.ob_plan)::numeric ELSE 0 END, 2) AS ob_ach,
            ROUND(COALESCE(a.waste, 0), 2) AS waste,
            ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
            ROUND(CASE WHEN p.waste_plan > 0 THEN (a.waste * 100.0 / p.waste_plan)::numeric ELSE 0 END, 2) AS waste_ach,
            ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
            ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
            ROUND(CASE WHEN p.quarry_plan > 0 THEN (a.quarry * 100.0 / p.quarry_plan)::numeric ELSE 0 END, 2) AS quarry_ach,
            ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
            ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
            ROUND(CASE WHEN p.ballast_plan > 0 THEN (a.ballast * 100.0 / p.ballast_plan)::numeric ELSE 0 END, 2) AS ballast_ach,
            ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
            ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
            ROUND(CASE WHEN p.biomass_plan > 0 THEN (a.biomass * 100.0 / p.biomass_plan)::numeric ELSE 0 END, 2) AS biomass_ach
        FROM tanggal
        LEFT JOIN actual a ON tanggal.date = a.tanggal
        LEFT JOIN plan p ON tanggal.date = p.tanggal
        ORDER BY tanggal.date
    """
    params = [date_start, date_end, 
              date_start, date_end,
              date_start, date_end,
              ]

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
        'sap', 'sap_plan', 'sap_ach',
        'topsoil', 'topsoil_plan', 'topsoil_ach',
        'ob', 'ob_plan', 'ob_ach',
        'waste', 'waste_plan', 'waste_ach',
        'quarry', 'quarry_plan', 'quarry_ach',
        'ballast', 'ballast_plan', 'ballast_ach',
        'biomass', 'biomass_plan', 'biomass_ach',
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols + non_ore_cols + non_ore_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['non_ore']        = df[non_ore_cols].sum(axis=1)
    df['non_ore_plan']   = df[non_ore_plan_cols].sum(axis=1)
    

    df['total_actual'] = df['limonite'] + df['saprolite'] + df['non_ore'] 
    df['total_plan']   = df['limonite_plan'] + df['saprolite_plan'] +  df['non_ore_plan']
    df['achievement']  = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    df['non_ore_ach']   = df.apply(lambda r: round((r['non_ore'] / r['non_ore_plan'] * 100), 2) if r['non_ore_plan'] > 0 else 0, axis=1)


    return JsonResponse({
        'x_data'       : df['tanggal'].astype(str).tolist(),
        # 'total_actual' : df['total_actual'].astype(float).tolist(),
        # 'total_plan'   : df['total_plan'].astype(float).tolist(),
        # 'achievement'  : df['achievement'].astype(float).tolist(),
        'total_actual' : df['total_actual'].round(1).tolist(),
        'total_plan'   : df['total_plan'].round(1).tolist(),
        'achievement'  : df['achievement'].round(1).tolist(),
    }, safe=False)

# kqms/dashboard/api/summary/mines/ore?filter_type=yearly&filter_year=2025
def get_detail_yearly(yearly,iup_filter=None):
    query = """
         WITH bulan AS (
            SELECT TO_CHAR(DATE_TRUNC('month', (DATE %s + (n || ' month')::interval)), 'YYYY-MM') AS bulan
            FROM generate_series(0, 11) AS n
        ),
        actual AS (
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
                SUM(CASE WHEN nama_material = 'SAP' THEN tonnage ELSE 0 END)::numeric AS sap,
                SUM(CASE WHEN nama_material = 'Top Soil' THEN tonnage ELSE 0 END)::numeric AS topsoil,
                SUM(CASE WHEN nama_material = 'OB' THEN tonnage ELSE 0 END)::numeric AS ob,
                SUM(CASE WHEN nama_material = 'Waste' THEN tonnage ELSE 0 END)::numeric AS waste,
                SUM(CASE WHEN nama_material = 'Quarry' THEN tonnage ELSE 0 END)::numeric AS quarry,
                SUM(CASE WHEN nama_material = 'Ballast' THEN tonnage ELSE 0 END)::numeric AS ballast,
                SUM(CASE WHEN nama_material = 'Biomass' THEN tonnage ELSE 0 END)::numeric AS biomass
            FROM view_mining_productions
            WHERE EXTRACT(YEAR FROM date_production) = %s
            GROUP BY TO_CHAR(date_production, 'YYYY-MM')
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
                SUM(sap)::numeric AS sap_plan,
                SUM(topsoil)::numeric AS topsoil_plan,
                SUM(ob)::numeric AS ob_plan,
                SUM(waste)::numeric AS waste_plan,
                SUM(quarry)::numeric AS quarry_plan,
                SUM(ballast)::numeric AS ballast_plan,
                SUM(biomass)::numeric AS biomass_plan
            FROM mining_plan_productions
            WHERE EXTRACT(YEAR FROM date_plan) = %s
            GROUP BY TO_CHAR(date_plan, 'YYYY-MM')
        )
        SELECT
            b.bulan,
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
                    ROUND(CASE WHEN p.sap_plan > 0 THEN (a.sap * 100.0 / p.sap_plan)::numeric ELSE 0 END, 2) AS sap_ach,
                    ROUND(COALESCE(a.topsoil, 0), 2) AS topsoil,
                    ROUND(COALESCE(p.topsoil_plan, 0), 2) AS topsoil_plan,
                    ROUND(CASE WHEN p.topsoil_plan > 0 THEN (a.topsoil * 100.0 / p.topsoil_plan)::numeric ELSE 0 END, 2) AS topsoil_ach,
                    ROUND(COALESCE(a.ob, 0), 2) AS ob,
                    ROUND(COALESCE(p.ob_plan, 0), 2) AS ob_plan,
                    ROUND(CASE WHEN p.ob_plan > 0 THEN (a.ob * 100.0 / p.ob_plan)::numeric ELSE 0 END, 2) AS ob_ach,
                    ROUND(COALESCE(a.waste, 0), 2) AS waste,
                    ROUND(COALESCE(p.waste_plan, 0), 2) AS waste_plan,
                    ROUND(CASE WHEN p.waste_plan > 0 THEN (a.waste * 100.0 / p.waste_plan)::numeric ELSE 0 END, 2) AS waste_ach,
                    ROUND(COALESCE(a.quarry, 0), 2) AS quarry,
                    ROUND(COALESCE(p.quarry_plan, 0), 2) AS quarry_plan,
                    ROUND(CASE WHEN p.quarry_plan > 0 THEN (a.quarry * 100.0 / p.quarry_plan)::numeric ELSE 0 END, 2) AS quarry_ach,
                    ROUND(COALESCE(a.ballast, 0), 2) AS ballast,
                    ROUND(COALESCE(p.ballast_plan, 0), 2) AS ballast_plan,
                    ROUND(CASE WHEN p.ballast_plan > 0 THEN (a.ballast * 100.0 / p.ballast_plan)::numeric ELSE 0 END, 2) AS ballast_ach,
                    ROUND(COALESCE(a.biomass, 0), 2) AS biomass,
                    ROUND(COALESCE(p.biomass_plan, 0), 2) AS biomass_plan,
                    ROUND(CASE WHEN p.biomass_plan > 0 THEN (a.biomass * 100.0 / p.biomass_plan)::numeric ELSE 0 END, 2) AS biomass_ach
        FROM bulan b
        LEFT JOIN actual a ON a.bulan = b.bulan
        LEFT JOIN plan p ON p.bulan = b.bulan
        ORDER BY b.bulan
    """

    params = [f"{yearly}-01-01", yearly, yearly]

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
        'sap', 'sap_plan', 'sap_ach',
        'topsoil', 'topsoil_plan', 'topsoil_ach',
        'ob', 'ob_plan', 'ob_ach',
        'waste', 'waste_plan', 'waste_ach',
        'quarry', 'quarry_plan', 'quarry_ach',
        'ballast', 'ballast_plan', 'ballast_ach',
        'biomass', 'biomass_plan', 'biomass_ach',
    ]

    df = pd.DataFrame(data, columns=columns)

    lim_cols = ['lglo', 'mglo', 'hglo','lim']
    sap_cols = ['lgso', 'mgso', 'hgso','sap']
    lim_plan_cols = [f + '_plan' for f in lim_cols]
    sap_plan_cols = [f + '_plan' for f in sap_cols]
    non_ore_cols = ['topsoil', 'ob', 'waste', 'quarry', 'ballast', 'biomass']
    non_ore_plan_cols = [f + '_plan' for f in non_ore_cols]

    # Konversi kolom ke numerik (handle string atau null)
    for col in lim_cols + sap_cols + lim_plan_cols + sap_plan_cols + non_ore_cols + non_ore_plan_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

    df['limonite']       = df[lim_cols].sum(axis=1)
    df['limonite_plan']  = df[lim_plan_cols].sum(axis=1)
    df['saprolite']      = df[sap_cols].sum(axis=1)
    df['saprolite_plan'] = df[sap_plan_cols].sum(axis=1)
    df['non_ore']        = df[non_ore_cols].sum(axis=1)
    df['non_ore_plan']   = df[non_ore_plan_cols].sum(axis=1)
    
    df['total_actual']  = df['limonite'] + df['saprolite'] + df['non_ore'] 
    df['total_plan']    = df['limonite_plan'] + df['saprolite_plan'] +  df['non_ore_plan']
    df['achievement']   = df.apply(lambda row: round((row['total_actual'] / row['total_plan'] * 100), 2) if row['total_plan'] > 0 else 0, axis=1)

    df['limonite_ach']  = df.apply(lambda r: round((r['limonite'] / r['limonite_plan'] * 100), 2) if r['limonite_plan'] > 0 else 0, axis=1)
    df['saprolite_ach'] = df.apply(lambda r: round((r['saprolite'] / r['saprolite_plan'] * 100), 2) if r['saprolite_plan'] > 0 else 0, axis=1)

    df['non_ore_ach']   = df.apply(lambda r: round((r['non_ore'] / r['non_ore_plan'] * 100), 2) if r['non_ore_plan'] > 0 else 0, axis=1)

    # Define month names
    x_data = df['bulan'].apply(lambda x: datetime.strptime(x, '%Y-%m').strftime('%b %y')).tolist()


    return JsonResponse({
        'x_data'       : x_data,
        'total_actual' : df['total_actual'].round(1).tolist(),
        'total_plan'   : df['total_plan'].round(1).tolist(),
        'achievement'  : df['achievement'].round(1).tolist(),
    }, safe=False)

def get_all_chart():
    query = """ 
          WITH actual_per_year AS (
                SELECT 
                    TO_CHAR(date_production, 'YYYY') AS tahun,
                    SUM(tonnage) AS total_tonnage
                FROM view_mining_productions
                GROUP BY TO_CHAR(date_production, 'YYYY')
            ),
            plan_per_year AS (
                SELECT 
                    TO_CHAR(date_plan, 'YYYY') AS tahun,
                    SUM(
                        COALESCE(topsoil, 0) + COALESCE(ob, 0) + COALESCE(lglo, 0) + COALESCE(mglo, 0) +
                        COALESCE(hglo, 0) + COALESCE(waste, 0) + COALESCE(mws, 0) + COALESCE(lgso, 0) +
                        COALESCE(mgso, 0) + COALESCE(hgso, 0) + COALESCE(lim, 0) + COALESCE(sap, 0) + 
                        COALESCE(quarry, 0) + COALESCE(ballast, 0) + COALESCE(biomass, 0)
                    ) AS plan_data
                FROM mining_plan_productions
                GROUP BY TO_CHAR(date_plan, 'YYYY')
            )
            SELECT 
                COALESCE(a.tahun, p.tahun) AS tahun,
                COALESCE(a.total_tonnage, 0) AS total_tonnage,
                COALESCE(p.plan_data, 0) AS plan_data
        FROM actual_per_year a
        FULL OUTER JOIN plan_per_year p ON a.tahun = p.tahun
        ORDER BY tahun
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['tahun','total_tonnage', 'plan_data'])
    df['total'] = pd.to_numeric(df['total_tonnage'], errors='coerce').fillna(0.0).round(2)
    df['plan_data'] = pd.to_numeric(df['plan_data'], errors='coerce').fillna(0.0).round(2)
    df['achievement'] = df.apply( lambda row: round(float(row['total']) / float(row['plan_data']) * 100, 2) if float(row['plan_data']) > 0 else 0,axis=1)

    return JsonResponse({
        'x_data'      : df['tahun'].tolist(), 
        'total_actual': df['total'].tolist(),
        'total_plan'  : df['plan_data'].tolist(),
        'achievement' : df['achievement'].tolist(),
    }, safe=False)
