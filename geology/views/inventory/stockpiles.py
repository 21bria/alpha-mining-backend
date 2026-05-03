# views.py
import logging
from django.http import JsonResponse
from django.db import connection
logger = logging.getLogger(__name__) #tambahkan ini untuk multi database.
import json
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
# Memanggil fungsi utility

def f2(v):
    return Decimal(v).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)


class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def to_float1(v):
    return round(float(v or 0), 1)

# Stockpile
# Stockpile
def get_inventory_stockpile(request):
    iup_filter = request.GET.get('iup_id')
    sale_filter = request.GET.get('material')
    area_filter = request.GET.getlist('sampling_area')     # multi

    # ================= PAGINATION =================
    page = int(request.GET.get('page', 1))
    per_page = 100
    offset = (page - 1) * per_page

    if not iup_filter:
        return JsonResponse({'error': 'iup_id wajib diisi'}, status=400)

    # ================= FILTER =================
    filters = ["t1.iup_id = %s"]
    params = [iup_filter]

    sale_mapping = {
        'LIM': 'HPAL',
        'SAP': 'RKEF',
    }

    if sale_filter:
        mapped_sale = sale_mapping.get(sale_filter.upper(), sale_filter)
        filters.append("t1.sale_adjust = %s")
        params.append(mapped_sale)

    if area_filter:
        filters.append(
            f"t1.stockpile IN ({', '.join(['%s'] * len(area_filter))})"
        )
        params.extend(area_filter)

    where_clause = " AND " + " AND ".join(filters) if filters else ""

    # ================= QUERY =================
    query = f"""
        WITH base_dome AS (
            -- ================= LEVEL DOME =================
            SELECT
                t1.iup_id,
                t1.stockpile,
                t1.pile_id,
                t1.nama_material,
                t1.total_ore::numeric AS tonnage,
                t1.released::numeric AS released,
                COALESCE(
                    CASE
                        WHEN t1.nama_material = t2.material THEN t2.tonnage
                        WHEN t1.nama_material = 'LIM' AND t2.material = 'SAP' THEN t2.tonnage
                        WHEN t1.nama_material = 'SAP' AND t2.material = 'LIM' THEN t2.tonnage
                        ELSE 0
                    END, 0
                )::numeric AS selling,

                -- ===== WEIGHTED NUMERATOR (PAKAI BALANCE) =====
                (t1.Ni::numeric    * (t1.total_ore - COALESCE(t2.tonnage,0))) AS ni_w,
                (t1.Co::numeric    * (t1.total_ore - COALESCE(t2.tonnage,0))) AS co_w,
                (t1.Al2O3::numeric * (t1.total_ore - COALESCE(t2.tonnage,0))) AS al2o3_w,
                (t1.CaO::numeric   * (t1.total_ore - COALESCE(t2.tonnage,0))) AS cao_w,
                (t1.Cr2O3::numeric * (t1.total_ore - COALESCE(t2.tonnage,0))) AS cr2o3_w,
                (t1.Fe::numeric    * (t1.total_ore - COALESCE(t2.tonnage,0))) AS fe_w,
                (t1.Mgo::numeric   * (t1.total_ore - COALESCE(t2.tonnage,0))) AS mgo_w,
                (t1.SiO2::numeric  * (t1.total_ore - COALESCE(t2.tonnage,0))) AS sio2_w,
                (t1.MC::numeric    * (t1.total_ore - COALESCE(t2.tonnage,0))) AS mc_w
            FROM view_inventory_by_dome t1
            LEFT JOIN view_selling_by_dome t2
                ON t2.iup_id = t1.iup_id
                AND t2.stockpile = t1.stockpile
                AND t2.dome = t1.pile_id
            WHERE t1.status_dome != 'Finished'
            {where_clause}
        ),
        stockpile_agg AS (
            -- ================= LEVEL STOCKPILE =================
            SELECT
                iup_id,
                stockpile,
                nama_material,
                SUM(tonnage) AS total_ore,
                SUM(released) AS total_released,
                SUM(selling) AS total_selling,
                SUM(tonnage - selling) AS balance,
                -- FINAL WEIGHTED AVERAGE
                SUM(ni_w)    / NULLIF(SUM(tonnage - selling), 0) AS ni,
                SUM(co_w)    / NULLIF(SUM(tonnage - selling), 0) AS co,
                SUM(al2o3_w) / NULLIF(SUM(tonnage - selling), 0) AS al2o3,
                SUM(cao_w)   / NULLIF(SUM(tonnage - selling), 0) AS cao,
                SUM(cr2o3_w) / NULLIF(SUM(tonnage - selling), 0) AS cr2o3,
                SUM(fe_w)    / NULLIF(SUM(tonnage - selling), 0) AS fe,
                SUM(mgo_w)   / NULLIF(SUM(tonnage - selling), 0) AS mgo,
                SUM(sio2_w)  / NULLIF(SUM(tonnage - selling), 0) AS sio2,
                SUM(mc_w)    / NULLIF(SUM(tonnage - selling), 0) AS mc,
                -- SM RATIO
                SUM(sio2_w) / NULLIF(SUM(mgo_w), 0) AS sm
            FROM base_dome
            GROUP BY iup_id, stockpile, nama_material
        )
        SELECT *
        FROM stockpile_agg
        ORDER BY stockpile, nama_material
        LIMIT %s OFFSET %s
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params + [per_page, offset])
        columns = [c[0] for c in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # ================= COUNT =================
    count_query = f"""
        SELECT COUNT(*)
        FROM (
            SELECT iup_id, stockpile, nama_material
            FROM view_inventory_by_dome t1
            WHERE t1.status_dome != 'Finished'
            {where_clause}
            GROUP BY iup_id, stockpile, nama_material
        ) x
    """

    with connection.cursor() as cursor:
        cursor.execute(count_query, params)
        total_data = cursor.fetchone()[0]

    # ================= POST PROCESS =================
    for row in data:
        for k in row:
            if isinstance(row[k], Decimal):
                row[k] = float(row[k])

    # ================= SUMMARY =================
    total_balance = sum(i['balance'] for i in data)

    def wavg(field):
        return (
            sum(i[field] * i['balance'] for i in data) / total_balance
            if total_balance else 0
        )

    summary = {
        'total_ore': sum(i['total_ore'] for i in data),
        'total_released': sum(i['total_released'] for i in data),
        'total_selling': sum(i['total_selling'] for i in data),
        'total_balance': total_balance,
        'avg_ni': wavg('ni'),
        'avg_co': wavg('co'),
        'avg_al2o3': wavg('al2o3'),
        'avg_cao': wavg('cao'),
        'avg_cr2o3': wavg('cr2o3'),
        'avg_fe': wavg('fe'),
        'avg_mgo': wavg('mgo'),
        'avg_sio2': wavg('sio2'),
        'avg_mc': wavg('mc'),
    }

    summary['sm_ratio'] = summary['avg_sio2'] / summary['avg_mgo'] if summary['avg_mgo'] else 0

    # ================= RESPONSE =================
    return JsonResponse({
        'data': data,
        'summary': summary,
        'pagination': {
            'more': len(data) == per_page,
            'current_page': page,
            'total_pages': (total_data // per_page) + (1 if total_data % per_page else 0),
            'total_data': total_data
        }
    })