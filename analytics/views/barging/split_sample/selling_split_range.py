from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connections, DatabaseError
from django.utils.html import escape
import json,re

# Fungsi untuk sanitasi input
def sanitize_input(value):
    if value is None:
        return None
    return escape(re.sub(r"[;'\"]", "", str(value)))

@login_required
def splitOfficialPage(request):
    return render(request, 'admin-selling/official/list-coa.html')

def splitSamplePage(request):
    return render(request, 'admin-selling/split/list-samples.html')

def samplesSplit(request):
    typeFilter   = request.GET.get('typeFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    codeFilter   = json.loads(request.GET.get('codeFilter', '[]'))

    # Filter list codeFilter
    codeFilter = [sanitize_input(code) for code in codeFilter if code]

    sql_query = """
       SELECT 
            TRIM(t1.code_lot)code_lot,
            TRIM(t1.code_sub) code_sub,
            TRIM(t1.sample_number) sample_number,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.ni) / SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END), 0) AS ni_split,
            COALESCE(SUM(t1.tonnage * t1.co) / SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.co IS NOT NULL THEN t1.tonnage ELSE 0 END), 0) AS co_split,
            COALESCE(SUM(t1.tonnage * t1.fe) / SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END), 0) AS fe_split,
            COALESCE(SUM(t1.tonnage * t1.mgo) / SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END), 0) AS mgo_split,
            COALESCE(SUM(t1.tonnage * t1.sio2) / SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0) AS sio2_split,
            COALESCE(t2.tonnage_pulp, 0) AS tonnage_pulp,
            COALESCE(t2.ni, 0) AS ni_pulp,
            COALESCE(t2.co, 0) AS co_pulp,
            COALESCE(t2.fe, 0) AS fe_pulp,
            COALESCE(t2.mgo, 0) AS mgo_pulp,
            COALESCE(t2.sio2, 0) AS sio2_pulp
        FROM details_selling_barge_split AS t1
        LEFT JOIN (
            SELECT 
                code_lot,
                code_sub,
                sample_number,
                COALESCE(SUM(tonnage), 0) AS tonnage_pulp,
                COALESCE(SUM(tonnage * ni) / SUM(CASE WHEN sample_number IS NOT NULL AND ni IS NOT NULL THEN tonnage ELSE 0 END), 0) AS ni,
                COALESCE(SUM(tonnage * co) / SUM(CASE WHEN sample_number IS NOT NULL AND co IS NOT NULL THEN tonnage ELSE 0 END), 0) AS co,
                COALESCE(SUM(tonnage * fe) / SUM(CASE WHEN sample_number IS NOT NULL AND fe IS NOT NULL THEN tonnage ELSE 0 END), 0) AS fe,
                COALESCE(SUM(tonnage * mgo) / SUM(CASE WHEN sample_number IS NOT NULL AND mgo IS NOT NULL THEN tonnage ELSE 0 END), 0) AS mgo,
                COALESCE(SUM(tonnage * sio2) / SUM(CASE WHEN sample_number IS NOT NULL AND sio2 IS NOT NULL THEN tonnage ELSE 0 END), 0) AS sio2
            FROM details_selling_barge_split_pulp
            GROUP BY code_lot,code_sub,sample_number) AS t2 ON t1.code_lot = t2.code_lot AND t1.code_sub=t2.code_sub
        WHERE 1=1
    """

     # **Filter pada query utama t1**
    params = []
    
    if typeFilter:
        sql_query += " AND t1.sale_adjust = %s"
        params.append(typeFilter)

    if startDate and endDate:
        sql_query += " AND t1.date_hauling BETWEEN %s AND %s"
        params.extend([startDate, endDate])

    if codeFilter:
        placeholders = ', '.join(['%s'] * len(codeFilter))
        sql_query += f" AND t1.code_lot IN ({placeholders})"
        params.extend(codeFilter)

    sql_query += """
        GROUP BY t1.code_lot, t1.code_sub, t1.sample_number, 
                 t2.tonnage_pulp, t2.ni, t2.co, t2.fe, t2.mgo, t2.sio2
        ORDER BY t1.code_lot, t1.code_lot ASC
    """

    # **Eksekusi Query**
    with connections['kqms_db'].cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return JsonResponse({'data': sql_data})

def splitOfficial(request):
    typeFilter   = request.GET.get('materialFilter')
    startDate    = request.GET.get('startDate')
    endDate      = request.GET.get('endDate')
    bulanFilter  = request.GET.get('bulanFilter')
    tahunFilter  = request.GET.get('tahunFilter')

    sql_query = """
        SELECT 
            TRIM(t1.code_lot) AS code_lot,
            TRIM(t1.barge_name) AS barge_name,
            COALESCE(SUM(t1.tonnage), 0) AS tonnage_split,              
            COALESCE(SUM(t1.tonnage * t1.ni) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS ni_split,
            COALESCE(SUM(t1.tonnage * t1.fe) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS fe_split,
            COALESCE(SUM(t1.tonnage * t1.mgo) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS mgo_split,
            COALESCE(SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END),0), 0) AS sio2_split,
            COALESCE(t2.tonnage_official, 0) AS tonnage_official,
            COALESCE(t2.ni, 0) AS ni_official,
            COALESCE(t2.fe, 0) AS fe_official, 
            COALESCE(t2.mgo, 0) AS mgo_official,
            COALESCE(t2.sio2, 0) AS sio2_official,
            -- SELISIH TONNAGE (split vs official)
            ABS(COALESCE(SUM(t1.tonnage) - t2.tonnage_official, 0)) AS tonnage_diff,
            -- SELISIH PERSEN (split vs official)
            COALESCE((
                (SUM(t1.tonnage * t1.ni)  / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.ni  IS NOT NULL THEN t1.tonnage ELSE 0 END), 0))
                - t2.ni)  / NULLIF(t2.ni, 0) * 100, 0) AS ni_diff,

            COALESCE((
                (SUM(t1.tonnage * t1.fe)  / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.fe  IS NOT NULL THEN t1.tonnage ELSE 0 END), 0))
                - t2.fe)  / NULLIF(t2.fe, 0) * 100, 0) AS fe_diff,

            COALESCE((
                (SUM(t1.tonnage * t1.mgo) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.mgo IS NOT NULL THEN t1.tonnage ELSE 0 END), 0))
                - t2.mgo) / NULLIF(t2.mgo, 0) * 100, 0) AS mgo_diff,
            COALESCE((
               (SUM(t1.tonnage * t1.sio2) / NULLIF(SUM(CASE WHEN t1.sample_number IS NOT NULL AND t1.sio2 IS NOT NULL THEN t1.tonnage ELSE 0 END), 0))
                - t2.sio2) / NULLIF(t2.sio2, 0) * 100, 0) AS sio2_diff
        FROM details_selling_barge_split AS t1
        LEFT JOIN (
            SELECT 
                product_code,
                COALESCE(SUM(tonnage), 0) AS tonnage_official,
                COALESCE(SUM(ni), 0) AS ni,
                COALESCE(SUM(fe), 0) AS fe,
                COALESCE(SUM(mgo), 0) AS mgo,
                COALESCE(SUM(sio2), 0) AS sio2,
                type_selling
            FROM sellings_official_view
            GROUP BY product_code, type_selling
        ) AS t2 ON t1.code_lot = t2.product_code
        WHERE 1=1
    """

    # **Filter pada query utama t1**
    filters = []
    if startDate and endDate:
        filters.append(f"t1.date_barge_out BETWEEN '{startDate}' AND '{endDate}'")
    if typeFilter:
        filters.append(f"t1.sale_adjust = '{typeFilter}'")
    if bulanFilter and tahunFilter:
        filters.append(f"EXTRACT(MONTH FROM t1.date_barge_out) = {bulanFilter} AND EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")
    elif tahunFilter:
        filters.append(f"EXTRACT(YEAR FROM t1.date_barge_out) = {tahunFilter}")

    if filters:
        sql_query += " AND " + " AND ".join(filters)

    sql_query += """
        GROUP BY t1.date_barge_in,t1.code_lot, t1.barge_name,
                 t2.tonnage_official, t2.ni, t2.fe, t2.mgo, t2.sio2
        ORDER BY t1.date_barge_in ASC
    """

    with connections['kqms_db'].cursor() as cursor:
        cursor.execute(sql_query)
        columns = [col[0] for col in cursor.description]
        sql_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    return JsonResponse({'data': sql_data})

