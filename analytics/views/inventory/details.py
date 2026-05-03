# views.py
import logging
from django.http import JsonResponse
from django.db import connections, DatabaseError
import calendar
from datetime import datetime, timedelta
logger = logging.getLogger(__name__) #tambahkan ini untuk multi database.
import json
from .....utils.db_utils import get_db_vendor

# Memanggil fungsi utility
db_vendor = get_db_vendor('kqms_db')

class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def to_float1(v):
    return round(float(v or 0), 1)

# Create Chart Ore
def get_chart_inventory_details(request):
    try:
        filter_type = request.GET.get('filter_type')
        year = request.GET.get('year')
        month = request.GET.get('month')
        week = request.GET.get('week')
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')

        x_labels    = []
        lim_in      = []
        lim_out     = []
        lim_balance = []
        sap_in      = []
        sap_out     = []
        sap_balance = []

        if filter_type =='range' and date_start and date_end: 
            if db_vendor == 'postgresql':
                query = """
                        WITH tanggal AS (
                            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                        ),
                        incoming AS (
                            SELECT
                                tgl_production::date AS date,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_in,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_in
                            FROM ore_productions op
                            LEFT JOIN materials m ON m.id = op.id_material
                            WHERE tgl_production BETWEEN %s AND %s
                            GROUP BY tgl_production
                        ),
                        outgoing AS (
                            SELECT
                                date_hauling::date AS date,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_out,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_out
                            FROM ore_selling_barging s
                            LEFT JOIN materials m ON m.id = s.id_material
                            WHERE date_hauling BETWEEN %s AND %s
                            GROUP BY date_hauling
                        ),
                        saldo_awal AS (
                            SELECT
                                -- Saldo awal LIM
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE tgl_production < %s AND m.nama_material = 'LIM'
                                ), 0) -
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE date_hauling < %s AND m.nama_material = 'LIM'
                                ), 0) AS lim_start,

                                -- Saldo awal SAP
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE tgl_production < %s AND m.nama_material = 'SAP'
                                ), 0) -
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE date_hauling < %s AND m.nama_material = 'SAP'
                                ), 0) AS sap_start
                        )

                        SELECT
                            TO_CHAR(t.date, 'YYYY-MM-DD') AS label,
                            COALESCE(i.lim_in, 0) AS lim_in,
                            COALESCE(o.lim_out, 0) AS lim_out,
                            COALESCE(i.sap_in, 0) AS sap_in,
                            COALESCE(o.sap_out, 0) AS sap_out,

                            -- Saldo berjalan LIM
                            SUM(COALESCE(i.lim_in, 0) - COALESCE(o.lim_out, 0))
                                OVER (ORDER BY t.date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                + (SELECT lim_start FROM saldo_awal) AS lim_balance,

                            -- Saldo berjalan SAP
                            SUM(COALESCE(i.sap_in, 0) - COALESCE(o.sap_out, 0))
                                OVER (ORDER BY t.date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                + (SELECT sap_start FROM saldo_awal) AS sap_balance

                        FROM tanggal t
                        LEFT JOIN incoming i ON t.date = i.date
                        LEFT JOIN outgoing o ON t.date = o.date
                        ORDER BY t.date;
                """
            else:
                 raise ValueError(f"Unsupported database vendor: {db_vendor}")
             
            params = [
                date_start, date_end,              # untuk tanggal (generate_series)
                date_start, date_end,              # untuk incoming
                date_start, date_end,              # untuk outgoing

                date_start, date_start,            # saldo_awal LIM: produksi dan selling
                date_start, date_start             # saldo_awal SAP: produksi dan selling
            ]

        elif filter_type =='weekly' and year and month and week:
            try:
                print("RECEIVED:", {"year": year, "month": month, "week": week})

                # Deteksi jika 'week' dalam format ISO (contoh: '2025-03')
                if '-' in str(week):
                    year_str, week_str = str(week).split('-')
                    year = int(year_str)
                    week = int(week_str)

                    # Hitung awal minggu (ISO): Senin minggu ke-X
                    start_date = datetime.strptime(f'{year}-W{week:02}-1', "%G-W%V-%u")
                    end_date = start_date + timedelta(days=6)
                else:
                    # Parsing normal year, month, week
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

                    # Koreksi akhir bulan
                    if end_date.month != month:
                        next_month = datetime(year, month, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)
            except Exception as e:
                return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)
            
            # SQL Query
            if db_vendor == 'postgresql':
                query = """
                    WITH tanggal AS (
                            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                        ),
                        incoming AS (
                            SELECT
                                tgl_production::date AS date,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_in,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_in
                            FROM ore_productions op
                            LEFT JOIN materials m ON m.id = op.id_material
                            WHERE tgl_production BETWEEN %s AND %s
                            GROUP BY tgl_production
                        ),
                        outgoing AS (
                            SELECT
                                date_hauling::date AS date,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN s.tonnage ELSE 0 END) AS lim_out,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN s.tonnage ELSE 0 END) AS sap_out
                            FROM ore_selling_barging s
                            LEFT JOIN materials m ON m.id = s.id_material
                            WHERE date_hauling BETWEEN %s AND %s
                            GROUP BY date_hauling
                        ),
                        daily AS (
                            SELECT
                                t.date,
                                COALESCE(i.lim_in, 0) AS lim_in,
                                COALESCE(o.lim_out, 0) AS lim_out,
                                COALESCE(i.sap_in, 0) AS sap_in,
                                COALESCE(o.sap_out, 0) AS sap_out
                            FROM tanggal t
                            LEFT JOIN incoming i ON t.date = i.date
                            LEFT JOIN outgoing o ON t.date = o.date
                        ),
                        saldo_awal AS (
                            SELECT
                                -- Saldo awal LIM
                                COALESCE((
                                    SELECT SUM(op.tonnage)
                                    FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE tgl_production < %s AND m.nama_material = 'LIM'
                                ), 0) -
                                COALESCE((
                                    SELECT SUM(s.tonnage)
                                    FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE date_hauling < %s AND m.nama_material = 'LIM'
                                ), 0) AS lim_start,

                                -- Saldo awal SAP
                                COALESCE((
                                    SELECT SUM(op.tonnage)
                                    FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE tgl_production < %s AND m.nama_material = 'SAP'
                                ), 0) -
                                COALESCE((
                                    SELECT SUM(s.tonnage)
                                    FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE date_hauling < %s AND m.nama_material = 'SAP'
                                ), 0) AS sap_start
                        )

                        SELECT
                            TRIM(TO_CHAR(date, 'Day')) AS label,
                            lim_in,
                            lim_out,
                            sap_in,
                            sap_out,
                            -- Saldo berjalan LIM
                            SUM(lim_in - lim_out) OVER (
                                ORDER BY date
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                            ) + (SELECT lim_start FROM saldo_awal) AS lim_balance,

                            -- Saldo berjalan SAP
                            SUM(sap_in - sap_out) OVER (
                                ORDER BY date
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                            ) + (SELECT sap_start FROM saldo_awal) AS sap_balance

                        FROM daily
                        GROUP BY TRIM(TO_CHAR(date, 'Day')), lim_in, lim_out, sap_in, sap_out, date
                        ORDER BY ARRAY_POSITION(
                            ARRAY['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
                            TRIM(TO_CHAR(date, 'Day'))
                        );
                """
            else:
                raise ValueError(f"Unsupported database vendor: {db_vendor}")

            params = [
                start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),       # untuk tanggal range

                start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),       # untuk incoming

                start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'),       # untuk outgoing

                start_date.strftime('%Y-%m-%d'),  # saldo_awal LIM (produksi < tanggal)
                start_date.strftime('%Y-%m-%d'),  # saldo_awal LIM (selling < tanggal)

                start_date.strftime('%Y-%m-%d'),  # saldo_awal SAP (produksi < tanggal)
                start_date.strftime('%Y-%m-%d')   # saldo_awal SAP (selling < tanggal)
            ]

        elif filter_type =='monthly' and year and month: 
            year  = int(year)
            month = int(month)

            # Ambil jumlah hari terakhir dalam bulan
            last_day = calendar.monthrange(year, month)[1]

            # Bangun tanggal awal dan akhir bulan
            tgl_pertama  = datetime(year, month, 1).date()
            tgl_terakhir = datetime(year, month, last_day).date()

            params = [
                tgl_pertama, tgl_terakhir,     # (1,2)
                tgl_pertama, tgl_terakhir,     # (3,4)
                tgl_pertama, tgl_terakhir,     # (5,6)
                tgl_pertama, tgl_pertama,      # (7,8)  
                tgl_pertama, tgl_pertama       # (9,10)
            ]
           
            if db_vendor == 'postgresql':
                query = """
                        WITH tanggal AS (
                            SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                        ),
                        incoming AS (
                            SELECT
                                tgl_production::date AS date,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_in,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_in
                            FROM ore_productions op
                            LEFT JOIN materials m ON m.id = op.id_material
                            WHERE tgl_production BETWEEN %s AND %s
                            GROUP BY tgl_production
                        ),
                        outgoing AS (
                            SELECT
                                date_hauling::date AS date,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_out,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_out
                            FROM ore_selling_barging s
                            LEFT JOIN materials m ON m.id = s.id_material
                            WHERE date_hauling BETWEEN %s AND %s
                            GROUP BY date_hauling
                        ),
                        saldo_awal AS (
                            SELECT
                                -- Saldo awal LIM
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE tgl_production < %s AND m.nama_material = 'LIM'
                                ), 0)
                                -
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE date_hauling < %s AND m.nama_material = 'LIM'
                                ), 0) AS lim_start,
                                
                                -- Saldo awal SAP
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE tgl_production < %s AND m.nama_material = 'SAP'
                                ), 0)
                                -
                                COALESCE((
                                    SELECT SUM(tonnage) FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE date_hauling < %s AND m.nama_material = 'SAP'
                                ), 0) AS sap_start
                        )
                        SELECT
                            TO_CHAR(t.date, 'DD') AS label,
                            COALESCE(i.lim_in, 0) AS lim_in,
                            COALESCE(o.lim_out, 0) AS lim_out,
                            -- Saldo LIM
                            SUM(COALESCE(i.lim_in, 0) - COALESCE(o.lim_out, 0))
                                OVER (ORDER BY t.date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                + (SELECT lim_start FROM saldo_awal) AS lim_balance,

                            COALESCE(i.sap_in, 0) AS sap_in,
                            COALESCE(o.sap_out, 0) AS sap_out,
                            -- Saldo SAP
                            SUM(COALESCE(i.sap_in, 0) - COALESCE(o.sap_out, 0))
                                OVER (ORDER BY t.date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                + (SELECT sap_start FROM saldo_awal) AS sap_balance

                        FROM tanggal t
                        LEFT JOIN incoming i ON t.date = i.date
                        LEFT JOIN outgoing o ON t.date = o.date
                        ORDER BY t.date;
                """
            else:
                raise ValueError(f"Unsupported database vendor: {db_vendor}")
            
    
        elif filter_type =='yearly' and year: 
            year = int(year)

            if db_vendor == 'postgresql':
                query = """
                     WITH bulan AS (
                            SELECT generate_series(1, 12) AS month
                        ),
                        incoming AS (
                            SELECT
                                EXTRACT(MONTH FROM op.tgl_production)::int AS month,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_in,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_in
                            FROM ore_productions op
                            LEFT JOIN materials m ON m.id = op.id_material
                            WHERE EXTRACT(YEAR FROM op.tgl_production) = %s
                            GROUP BY EXTRACT(MONTH FROM op.tgl_production)
                        ),
                        outgoing AS (
                            SELECT
                                EXTRACT(MONTH FROM s.date_hauling)::int AS month,
                                SUM(CASE WHEN m.nama_material = 'LIM' THEN s.tonnage ELSE 0 END) AS lim_out,
                                SUM(CASE WHEN m.nama_material = 'SAP' THEN s.tonnage ELSE 0 END) AS sap_out
                            FROM ore_selling_barging s
                            LEFT JOIN materials m ON m.id = s.id_material
                            WHERE EXTRACT(YEAR FROM s.date_hauling) = %s
                            GROUP BY EXTRACT(MONTH FROM s.date_hauling)
                        ),
                        saldo_awal AS (
                            SELECT
                                -- LIM
                                COALESCE((
                                    SELECT SUM(op.tonnage)
                                    FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE EXTRACT(YEAR FROM op.tgl_production) < %s AND m.nama_material = 'LIM'
                                ), 0) -
                                COALESCE((
                                    SELECT SUM(s.tonnage)
                                    FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE EXTRACT(YEAR FROM s.date_hauling) < %s AND m.nama_material = 'LIM'
                                ), 0) AS lim_start,
                                
                                -- SAP
                                COALESCE((
                                    SELECT SUM(op.tonnage)
                                    FROM ore_productions op
                                    LEFT JOIN materials m ON m.id = op.id_material
                                    WHERE EXTRACT(YEAR FROM op.tgl_production) < %s AND m.nama_material = 'SAP'
                                ), 0) -
                                COALESCE((
                                    SELECT SUM(s.tonnage)
                                    FROM ore_selling_barging s
                                    LEFT JOIN materials m ON m.id = s.id_material
                                    WHERE EXTRACT(YEAR FROM s.date_hauling) < %s AND m.nama_material = 'SAP'
                                ), 0) AS sap_start
                        )
                        SELECT
                            TO_CHAR(TO_DATE(bulan.month::text, 'MM'), 'Mon') AS label,
                            COALESCE(i.lim_in, 0) AS lim_in,
                            COALESCE(o.lim_out, 0) AS lim_out,
                            SUM(COALESCE(i.lim_in, 0) - COALESCE(o.lim_out, 0))
                                OVER (ORDER BY bulan.month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                + (SELECT lim_start FROM saldo_awal) AS lim_balance,
                            
                            COALESCE(i.sap_in, 0) AS sap_in,
                            COALESCE(o.sap_out, 0) AS sap_out,
                            SUM(COALESCE(i.sap_in, 0) - COALESCE(o.sap_out, 0))
                                OVER (ORDER BY bulan.month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                + (SELECT sap_start FROM saldo_awal) AS sap_balance

                        FROM bulan
                        LEFT JOIN incoming i ON bulan.month = i.month
                        LEFT JOIN outgoing o ON bulan.month = o.month
                        ORDER BY bulan.month;
                """
            else:
                raise ValueError(f"Unsupported database vendor: {db_vendor}")
            
            params = [year,year,year,year,year,year]

        elif filter_type =='all':
            if db_vendor == 'postgresql':
                query = """
                    WITH incoming AS (
                        SELECT
                            EXTRACT(YEAR FROM tgl_production)::int AS year,
                            SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_in,
                            SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_in
                        FROM ore_productions op
                        LEFT JOIN materials m ON m.id = op.id_material
                        GROUP BY EXTRACT(YEAR FROM tgl_production)
                    ),
                    outgoing AS (
                        SELECT
                            EXTRACT(YEAR FROM date_hauling)::int AS year,
                            SUM(CASE WHEN m.nama_material = 'LIM' THEN tonnage ELSE 0 END) AS lim_out,
                            SUM(CASE WHEN m.nama_material = 'SAP' THEN tonnage ELSE 0 END) AS sap_out
                        FROM ore_selling_barging s
                        LEFT JOIN materials m ON m.id = s.id_material
                        GROUP BY EXTRACT(YEAR FROM date_hauling)
                    )
                    SELECT
                        COALESCE(i.year, o.year) AS label,
                        COALESCE(i.lim_in, 0) AS lim_in,
                        COALESCE(o.lim_out, 0) AS lim_out,
                        SUM(COALESCE(i.lim_in, 0) - COALESCE(o.lim_out, 0))
                            OVER (ORDER BY COALESCE(i.year, o.year)) AS lim_balance,
                        COALESCE(i.sap_in, 0) AS sap_in,
                        COALESCE(o.sap_out, 0) AS sap_out,
                        SUM(COALESCE(i.sap_in, 0) - COALESCE(o.sap_out, 0))
                            OVER (ORDER BY COALESCE(i.year, o.year)) AS sap_balance

                    FROM incoming i
                    FULL OUTER JOIN outgoing o ON i.year = o.year
                    ORDER BY label;
                """
            else:
                raise ValueError(f"Unsupported database vendor: {db_vendor}")
            params = []

        else:
            return JsonResponse({'error': 'Invalid or incomplete filter parameters'}, status=400)

        # Eksekusi query
        with connections['kqms_db'].cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        for row in results:
            x_labels.append(str(row[0]))
            lim_in.append(round(float(row[1]), 0))
            lim_out.append(round(float(row[2]), 0))
            lim_balance.append(round(float(row[3]), 0))
            sap_in.append(round(float(row[4]), 0))
            sap_out.append(round(float(row[5]), 0))
            sap_balance.append(round(float(row[6]), 0))

        return JsonResponse({
            'x_data'        : x_labels,
            'y_lim_in'      : lim_in,
            'y_lim_out'     : lim_out,
            'y_lim_balance' : lim_balance,
            'y_sap_in'      : sap_in,
            'y_sap_out'     : sap_out,
            'y_sap_balance' : sap_balance
        })

    except DatabaseError:
        logger.exception("DB Error in get_chart_inventory")
        return JsonResponse({'error': 'Database error'}, status=500)
    
    except Exception as e:
        logger.exception("Unexpected error in get_chart_inventory")
        return JsonResponse({'error': str(e)}, status=500)

# Ach. Ore Production
def get_grade_class(ni, mgo, fe):
    if ni is None or mgo is None or fe is None:
        return "NULL"
    if ni >= 1.6 and mgo >= 7.0 and fe <= 27.0:
        return "HGS"
    elif 1.2 <= ni < 1.6 and mgo >= 7.0 and fe <= 27.0:
        return "MGS"
    elif ni < 1.2 and 7.0 <= mgo <= 20.0 and fe <= 27.0:
        return "LGS"
    elif ni >= 1.1 and mgo < 7.0 and fe >= 27.0:
        return "HGL"
    elif ni < 1.1 and mgo < 7.0 and fe >= 27.0:
        return "LGL"
    elif ni < 0.9 and mgo < 7.0 and fe < 27.0:
        return "OB"
    elif ni < 1.2 and mgo > 20.0 and fe >= 27.0:
        return "WASTE"
    else:
        return "???"

    
def get_grade_roa(request):
    try:
        filter_type = request.GET.get('filter_type')
        year = request.GET.get('year')
        month = request.GET.get('month')
        week = request.GET.get('week')
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')
        filter_date = request.GET.get('filter_date')

        # WHERE clause dan parameter
        where_clause = "WHERE 1=1"
        params = []

        if filter_type =='daily' and filter_date:
            where_clause += " AND tgl_production = %s "
            params += [filter_date]
        if filter_type =='range' and date_start and date_end:
            where_clause += " AND tgl_production BETWEEN %s AND %s"
            params += [date_start, date_end]
        elif filter_type =='weekly' and week:
            where_clause += " AND TO_CHAR(tgl_production, 'IYYY-IW') = %s"
            params.append(week)
        elif filter_type =='monthly' and year and month:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s AND EXTRACT(MONTH FROM tgl_production) = %s"
            params += [year, month]
        elif filter_type =='yearly' and year:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s"
            params.append(year)
        elif filter_type =='all':
            pass  # Semua data
        elif filter_type not in ['daily', 'range', 'weekly', 'yearly', 'all']:
            return JsonResponse({'error': 'Invalid filter type'}, status=400)

        # Query utama
        sql_query = f"""
                    SELECT
                            nama_material,
                            SUM(tonnage) AS total_ore,
                            SUM(CASE WHEN ROA_Ni  IS NOT NULL AND sample_number  <> 'Unprepared' THEN tonnage ELSE 0 END) AS released,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Ni) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as ni,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Co) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as co,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Al2O3) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as al2o3,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_CaO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as cao,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Cr2O3) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as cr2o3,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Fe2O3) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as fe2o3,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Fe) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as fe,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_MgO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as mgo,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_MC) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as mc,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_SiO2) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as sio2,
                            ROUND(COALESCE(
                                (
                            SUM(tonnage * ROA_SiO2) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)) /
                            (NULLIF(SUM(tonnage * ROA_MgO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0),0) + 0.000001), 0
                            )::numeric, 2) as sm
                        FROM details_roa
                    {where_clause}
                    GROUP BY nama_material
            """

        with connections['kqms_db'].cursor() as cursor:
            cursor.execute(sql_query, params)
            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for row in result:
            row['total_ore'] = round(float(row['total_ore']), 1)
            row['released']  = round(float(row['released']), 1)
            row['ni']        = round(float(row['ni']), 2)
            row['co']        = round(float(row['co']), 2)
            row['al2o3']     = round(float(row['al2o3']), 2)
            row['cao']       = round(float(row['cao']), 2)
            row['cr2o3']     = round(float(row['cr2o3']), 2)
            row['fe']        = round(float(row['fe']), 2)
            row['mgo']       = round(float(row['mgo']), 2)
            row['sio2']      = round(float(row['sio2']), 2)
            row['mc']        = round(float(row['mc']), 2)
            row['sm']        = round(float(row['sm']), 2)
            row['grade']     = get_grade_class(row['ni'], row['mgo'], row['fe'])

        return JsonResponse({
            'data': result,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_stockpile_roa(request):
    try:
        per_page = int(request.GET.get('per_page', 10))  # misal default 10

        materialFilter = request.GET.get('material', '')
        filter_type = request.GET.get('filter_type')
        year = request.GET.get('year')
        month = request.GET.get('month')
        week = request.GET.get('week')
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')
        filter_date = request.GET.get('filter_date')

        # WHERE clause dan parameter
        where_clause = "WHERE 1=1"
        params = []

        if materialFilter:
            where_clause += " AND nama_material = %s"
            params.append(materialFilter)
        
        if filter_type =='daily' and filter_date:
            where_clause += " AND tgl_production = %s "
            params += [filter_date]
        if filter_type =='range' and date_start and date_end:
            where_clause += " AND tgl_production BETWEEN %s AND %s"
            params += [date_start, date_end]
        elif filter_type =='weekly' and week:
            where_clause += " AND TO_CHAR(tgl_production, 'IYYY-IW') = %s"
            params.append(week)
        elif filter_type =='monthly' and year and month:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s AND EXTRACT(MONTH FROM tgl_production) = %s"
            params += [year, month]
        elif filter_type =='yearly' and year:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s"
            params.append(year)
        elif filter_type =='all':
            pass  # Semua data
        elif filter_type not in ['daily', 'range', 'weekly', 'yearly', 'all']:
            return JsonResponse({'error': 'Invalid filter type'}, status=400)

        # Query utama
        sql_query = f"""
                SELECT * FROM (
                    SELECT
                            stockpile,
                            nama_material,
                            SUM(tonnage) AS total_ore,
                            SUM(CASE WHEN ROA_Ni  IS NOT NULL AND sample_number  <> 'Unprepared' THEN tonnage ELSE 0 END) AS released,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Ni) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as ni,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Co) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as co,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Al2O3) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as al2o3,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_CaO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as cao,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Cr2O3) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as cr2o3,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Fe2O3) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as fe2o3,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Fe) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as fe,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_MgO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as mgo,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_MC) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as mc,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_SiO2) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as sio2,
                            ROUND(COALESCE(
                                (
                            SUM(tonnage * ROA_SiO2) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)) /
                            (NULLIF(SUM(tonnage * ROA_MgO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0),0) + 0.000001), 0
                            )::numeric, 2) as sm
                        FROM details_roa
                    {where_clause}
                    GROUP BY stockpile, nama_material
                ) AS sub
                ORDER BY RANDOM()
                LIMIT %s
            """
        params.extend([per_page])

        with connections['kqms_db'].cursor() as cursor:
            cursor.execute(sql_query, params)
            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]

        grandTotalOre      = 0
        grandTotalRelease  = 0
        # Data untuk product grade
        data_Ni    = []
        data_Co    = []
        data_Al2O3 = []
        data_CaO   = []
        data_Cr2O3 = []
        data_Fe    = []
        data_Mgo   = []
        data_SiO2  = []
        data_MC    = []
        data_SM    = []

        # Menghitung grand total dan product grade
        for row in result:
                grandTotalOre += float(row['total_ore'])
                grandTotalRelease    += float(row['released'])

                # Hitung Product Grade
                data_Ni.append(row['released'] * float(row['ni']))
                data_Co.append(row['released'] * float(row['co']))
                data_Al2O3.append(row['released'] * float(row['al2o3']))
                data_CaO.append(row['released'] * float(row['cao']))
                data_Cr2O3.append(row['released'] * float(row['cr2o3']))
                data_Fe.append(row['released'] * float(row['fe']))
                data_Mgo.append(row['released'] * float(row['mgo']))
                data_SiO2.append(row['released'] * float(row['sio2']))
                data_MC.append(row['released'] * float(row['mc']))
                data_SM.append(row['released'] * float(row['sm']))
                row['grade'] = get_grade_class(float(row['ni']), float(row['mgo']), float(row['fe']))

        return JsonResponse({
            'data': result,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_dome_roa(request):
    try:
        per_page = int(request.GET.get('per_page', 6))  # misal default 10

        materialFilter = request.GET.get('material', '')
        filter_type = request.GET.get('filter_type')
        year = request.GET.get('year')
        month = request.GET.get('month')
        week = request.GET.get('week')
        date_start = request.GET.get('date_start')
        date_end = request.GET.get('date_end')
        filter_date = request.GET.get('filter_date')

        # WHERE clause dan parameter
        where_clause = "WHERE 1=1"
        params = []

        if materialFilter:
            where_clause += " AND nama_material = %s"
            params.append(materialFilter)

        if filter_type =='daily' and filter_date:
            where_clause += " AND tgl_production = %s "
            params += [filter_date]
        elif filter_type =='range' and date_start and date_end:
            where_clause += " AND tgl_production BETWEEN %s AND %s"
            params += [date_start, date_end]
        elif filter_type =='weekly' and week:
            where_clause += " AND TO_CHAR(tgl_production, 'IYYY-IW') = %s"
            params.append(week)
        elif filter_type =='monthly' and year and month:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s AND EXTRACT(MONTH FROM tgl_production) = %s"
            params += [year, month]
        elif filter_type =='yearly' and year:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s"
            params.append(year)
        elif filter_type =='all':
            pass  # Semua data
        elif filter_type not in ['daily', 'range', 'weekly', 'yearly', 'all']:
            return JsonResponse({'error': 'Invalid filter type'}, status=400)

        # Query utama
        sql_query = f"""
                SELECT * FROM (
                    SELECT
                            pile_id,
                            nama_material,
                            SUM(tonnage) AS total_ore,
                            SUM(CASE WHEN ROA_Ni  IS NOT NULL AND sample_number  <> 'Unprepared' THEN tonnage ELSE 0 END) AS released,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_Ni) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as ni,
                             COALESCE(ROUND((
                                SUM(tonnage * ROA_Fe) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as fe,
                            COALESCE(ROUND((
                                SUM(tonnage * ROA_MgO) / NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                            )::numeric, 2), 0) as mgo
                        FROM details_roa
                    {where_clause}
                    GROUP BY pile_id, nama_material
                ) AS sub
                ORDER BY RANDOM()
                LIMIT %s
            """
        params.extend([per_page])

        with connections['kqms_db'].cursor() as cursor:
            cursor.execute(sql_query, params)
            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]


        # Menghitung grand total dan product grade
        for row in result:
            row['total_ore'] = round(float(row['total_ore']), 1)
            row['released']  = round(float(row['released']), 1)
            row['ni']        = round(float(row['ni']), 2)
            row['mgo']       = round(float(row['mgo']), 2)
            row['grade']     = get_grade_class(row['ni'], row['mgo'], row['fe'])

        return JsonResponse({
            'data': result,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

