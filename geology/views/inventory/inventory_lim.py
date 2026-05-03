# views.py
import logging
from django.http import JsonResponse
from django.db import connections, DatabaseError,connection
import pandas as pd
import calendar
from datetime import datetime, timedelta
from geology.services.utils import validate_month,validate_year
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
# /api/geology/raw/inventory/list/?iup_id=1&page=1
# /api/geology/raw/inventory/list/?iup_id=1&sale_filter=Finished&page=1
# Get Inventory

def build_inventory_filters(request):
    iup_filter   = request.GET.get('iup_id')
    area_filter  = request.GET.get('areaFilter')          # single
    point_filter = request.GET.getlist('pointFilter')     # multi

    if not iup_filter:
        return None, None, JsonResponse({'error': 'iup_id wajib diisi'}, status=400)

    where_conditions = [
        "t1.iup_id = %s",
        "t1.status_dome != %s",
        "t1.sale_adjust = %s",
    ]
    params = [iup_filter, 'Finished','HPAL']

    sale_mapping = {
        'LIM': 'HPAL',
        'SAP': 'RKEF',
    }


    if area_filter not in [None, '']:
        where_conditions.append("t1.stockpile = %s")
        params.append(area_filter)

    if point_filter:
        placeholders = ", ".join(["%s"] * len(point_filter))
        where_conditions.append(f"t1.pile_id IN ({placeholders})")
        params.extend(point_filter)

    where_clause = "WHERE " + " AND ".join(where_conditions)
    return where_clause, params, None

def fetch_all_as_dict(query, params):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def fetch_one_value(query, params):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()[0]

def convert_numeric_fields(rows, numeric_fields):
    for item in rows:
        for field in numeric_fields:
            if field in item and item[field] is not None:
                item[field] = float(item[field])
    return rows

def build_summary(rows):
    total_released = sum(item.get('released') or 0 for item in rows)
    total_ore = sum(item.get('total_ore') or 0 for item in rows)
    total_selling = sum(item.get('total_selling') or 0 for item in rows)
    total_balance = sum(item.get('balance') or 0 for item in rows)

    def weighted_avg(field):
        if total_balance == 0:
            return 0
        return sum((item.get(field) or 0) * (item.get('balance') or 0) for item in rows) / total_balance

    return {
        'total_ore': round(total_ore, 2),
        'total_released': round(total_released, 2),
        'total_selling': round(total_selling, 2),
        'total_balance': round(total_balance, 2),
        'avg_ni': weighted_avg('ni'),
        'avg_co': weighted_avg('co'),
        'avg_al2o3': weighted_avg('al2o3'),
        'avg_cao': weighted_avg('cao'),
        'avg_cr2o3': weighted_avg('cr2o3'),
        'avg_fe': weighted_avg('fe'),
        'avg_mgo': weighted_avg('mgo'),
        'avg_sio2': weighted_avg('sio2'),
        'avg_mc': weighted_avg('mc'),
        'avg_sm': weighted_avg('sm'),
    }

def get_data_inventory_lim(request):
    page = int(request.GET.get('page', 1))
    per_page = 100
    offset = (page - 1) * per_page

    where_clause, params, error_response = build_inventory_filters(request)
    if error_response:
        return error_response

    count_query = f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                t1.iup_id,
                t1.iup_code,
                t1.stockpile,
                t1.pile_id
            FROM view_inventory_by_dome AS t1
            LEFT JOIN view_selling_by_dome AS t2
                ON t2.iup_id = t1.iup_id
                AND t2.stockpile = t1.stockpile
                AND t2.dome = t1.pile_id
                AND t2.sale_adjust = 'HPAL'
            {where_clause}
            GROUP BY
                t1.iup_id, t1.iup_code, t1.stockpile, t1.pile_id,
                t1.total_ore, t1.released, t1.nama_material,
                t1.ni, t1.co, t1.al2o3, t1.cao, t1.cr2o3,
                t1.fe, t1.mgo, t1.sio2, t1.mc, t1.sm
        ) AS sub
    """
    total_data = fetch_one_value(count_query, params)

    data_query = f"""
        SELECT
            t1.iup_id,
            t1.iup_code,
            t1.stockpile,
            t1.pile_id,
            t1.total_ore,
            t1.released,
            t1.nama_material,
            COALESCE(ROUND(SUM(
                CASE
                    WHEN t1.nama_material = t2.material THEN t2.tonnage
                    WHEN t1.nama_material = 'LIM' AND t2.material = 'SAP' THEN t2.tonnage
                    WHEN t1.nama_material = 'SAP' AND t2.material = 'LIM' THEN t2.tonnage
                    ELSE 0
                END
            )::numeric, 2), 0) AS total_selling,
            ROUND((
                t1.total_ore - COALESCE(SUM(
                    CASE
                        WHEN t1.nama_material = t2.material THEN t2.tonnage
                        WHEN t1.nama_material = 'LIM' AND t2.material = 'SAP' THEN t2.tonnage
                        WHEN t1.nama_material = 'SAP' AND t2.material = 'LIM' THEN t2.tonnage
                        ELSE 0
                    END
                ),0)
            )::numeric, 2) AS balance,
            t1.ni,
            t1.co,
            t1.al2o3,
            t1.cao,
            t1.cr2o3,
            t1.fe,
            t1.mgo,
            t1.sio2,
            t1.mc,
            t1.sm
        FROM view_inventory_by_dome AS t1
        LEFT JOIN view_selling_by_dome AS t2
            ON t2.iup_id = t1.iup_id
            AND t2.stockpile = t1.stockpile
            AND t2.dome = t1.pile_id
            --AND t2.sale_adjust = 'HPAL'
        {where_clause}
        GROUP BY
            t1.iup_id,
            t1.iup_code,
            t1.stockpile,
            t1.pile_id,
            t1.total_ore,
            t1.released,
            t1.nama_material,
            t1.ni,
            t1.co,
            t1.al2o3,
            t1.cao,
            t1.cr2o3,
            t1.fe,
            t1.mgo,
            t1.sio2,
            t1.mc,
            t1.sm
        ORDER BY t1.nama_material ASC, t1.stockpile ASC
        LIMIT %s OFFSET %s
    """
    sql_data = fetch_all_as_dict(data_query, params + [per_page, offset])

    numeric_fields = [
        'total_ore', 'released', 'total_selling', 'balance',
        'ni', 'co', 'al2o3', 'cao', 'cr2o3', 'fe', 'mgo', 'sio2', 'mc', 'sm'
    ]
    sql_data = convert_numeric_fields(sql_data, numeric_fields)

    summary = build_summary(sql_data)

    return JsonResponse({
        'data': sql_data,
        'summary': summary,
        'pagination': {
            'more': len(sql_data) == per_page,
            'total_pages': (total_data // per_page) + (1 if total_data % per_page > 0 else 0),
            'current_page': page,
            'total_data': total_data
        }
    })