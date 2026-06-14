# views.py
import logging
from django.http import JsonResponse
from django.db import connection
logger = logging.getLogger(__name__) #tambahkan ini untuk multi database.
import json
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP


def f2(v):
    return Decimal(v).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)


class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def to_float1(v):
    return round(float(v or 0), 1)


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
 

def get_data_inventory_psi(request):
    page = int(request.GET.get("page", 1))
    per_page = 100
    offset = (page - 1) * per_page

    iup_id = request.GET.get("iup_id")
    material = request.GET.get("material")
    area = request.GET.get("areaFilter")
    point_filter = request.GET.getlist("pointFilter")

    if not iup_id:
        return JsonResponse({"error": "iup_id wajib diisi"}, status=400)

    where = [
        "i.total_ore > 0",
        "i.status_dome = 'Continue'",
        "i.iup_id = %s",
    ]
    params = [iup_id]

    if material not in [None, ""]:
        where.append("i.nama_material = %s")
        params.append(material)

    if area not in [None, ""]:
        where.append("TRIM(i.stockpile) = %s")
        params.append(area)

    if point_filter:
        placeholders = ", ".join(["%s"] * len(point_filter))
        where.append(f"TRIM(i.pile_id) IN ({placeholders})")
        params.extend(point_filter)

    where_sql = "WHERE " + " AND ".join(where)

    base_query = f"""
        FROM view_inventory_by_dome i
        LEFT JOIN view_geology_sample_psi_summary p
            ON p.iup_id = i.iup_id
           AND p.id_pile = i.id_pile
        {where_sql}
    """

    data_query = f"""
        SELECT
            i.iup_id,
            i.iup_code,
            i.stockpile,
            i.pile_id,
            i.id_pile,
            i.nama_material,

            i.total_ore AS inventory_total_ore,
            COALESCE(p.psi_allocated_tonnage, 0) AS psi_allocated_tonnage,
            COALESCE(p.psi_allocated_tonnage, 0) - i.total_ore AS diff_tonnage,

            ROUND((
                ((COALESCE(p.psi_allocated_tonnage, 0) - i.total_ore)
                / NULLIF(i.total_ore, 0)) * 100
            )::numeric, 2) AS diff_tonnage_pct,

            i.ni::double precision AS inventory_ni,
            p.ni AS psi_ni,
            ROUND((
                ((p.ni - i.ni::double precision)
                / NULLIF(i.ni::double precision, 0)) * 100
            )::numeric, 2) AS diff_ni_pct,

            i.fe::double precision AS inventory_fe,
            p.fe AS psi_fe,
            ROUND((
                ((p.fe - i.fe::double precision)
                / NULLIF(i.fe::double precision, 0)) * 100
            )::numeric, 2) AS diff_fe_pct,

            i.mgo::double precision AS inventory_mgo,
            p.mgo AS psi_mgo,
            ROUND((
                ((p.mgo - i.mgo::double precision)
                / NULLIF(i.mgo::double precision, 0)) * 100
            )::numeric, 2) AS diff_mgo_pct,

            i.sio2::double precision AS inventory_sio2,
            p.sio2 AS psi_sio2,
            ROUND((
                ((p.sio2 - i.sio2::double precision)
                / NULLIF(i.sio2::double precision, 0)) * 100
            )::numeric, 2) AS diff_sio2_pct,

            i.sm::double precision AS inventory_sm,
            p.sm AS psi_sm,
            ROUND((
                ((p.sm - i.sm::double precision)
                / NULLIF(i.sm::double precision, 0)) * 100
            )::numeric, 2) AS diff_sm_pct,

            CASE
                WHEN p.id_pile IS NULL THEN 'NO_PSI'
                ELSE 'HAS_PSI'
            END AS psi_status

        {base_query}
        ORDER BY i.nama_material ASC, i.stockpile ASC, i.pile_id ASC
        LIMIT %s OFFSET %s
    """

    count_query = f"""
        SELECT COUNT(*)
        {base_query}
    """

    summary_query = f"""
       SELECT
        COALESCE(ROUND(SUM(i.total_ore)::numeric, 2), 0) AS inventory_total_ore,
        COALESCE(ROUND(SUM(COALESCE(p.psi_allocated_tonnage, 0))::numeric, 2), 0) AS psi_allocated_tonnage,
        COALESCE(ROUND(SUM(COALESCE(p.psi_allocated_tonnage, 0) - i.total_ore)::numeric, 2), 0) AS diff_tonnage,

        COUNT(*) AS total_dome,
        COUNT(p.id_pile) AS total_has_psi,
        COUNT(*) - COUNT(p.id_pile) AS total_no_psi,

        -- Inventory Avg
        ROUND(
            COALESCE(
                SUM(i.total_ore * i.ni::double precision)
                / NULLIF(SUM(i.total_ore), 0),
                0
            )::numeric,
            2
        ) AS inventory_avg_ni,

        ROUND(
            COALESCE(
                SUM(i.total_ore * i.fe::double precision)
                / NULLIF(SUM(i.total_ore), 0),
                0
            )::numeric,
            2
        ) AS inventory_avg_fe,

        ROUND(
            COALESCE(
                SUM(i.total_ore * i.mgo::double precision)
                / NULLIF(SUM(i.total_ore), 0),
                0
            )::numeric,
            2
        ) AS inventory_avg_mgo,

        ROUND(
            COALESCE(
                SUM(i.total_ore * i.sio2::double precision)
                / NULLIF(SUM(i.total_ore), 0),
                0
            )::numeric,
            2
        ) AS inventory_avg_sio2,

        ROUND(
            COALESCE(
                SUM(i.total_ore * i.sm::double precision)
                / NULLIF(SUM(i.total_ore), 0),
                0
            )::numeric,
            2
        ) AS inventory_avg_sm,

        -- PSI Avg
        ROUND(
            COALESCE(
                SUM(p.psi_allocated_tonnage * p.ni)
                / NULLIF(SUM(p.psi_allocated_tonnage), 0),
                0
            )::numeric,
            2
        ) AS psi_avg_ni,

        ROUND(
            COALESCE(
                SUM(p.psi_allocated_tonnage * p.fe)
                / NULLIF(SUM(p.psi_allocated_tonnage), 0),
                0
            )::numeric,
            2
        ) AS psi_avg_fe,

        ROUND(
            COALESCE(
                SUM(p.psi_allocated_tonnage * p.mgo)
                / NULLIF(SUM(p.psi_allocated_tonnage), 0),
                0
            )::numeric,
            2
        ) AS psi_avg_mgo,

        ROUND(
            COALESCE(
                SUM(p.psi_allocated_tonnage * p.sio2)
                / NULLIF(SUM(p.psi_allocated_tonnage), 0),
                0
            )::numeric,
            2
        ) AS psi_avg_sio2,

        ROUND(
            COALESCE(
                SUM(p.psi_allocated_tonnage * p.sm)
                / NULLIF(SUM(p.psi_allocated_tonnage), 0),
                0
            )::numeric,
            2
        ) AS psi_avg_sm

        {base_query}
    """

    total_data = fetch_one_value(count_query, params)
    sql_data = fetch_all_as_dict(data_query, params + [per_page, offset])
    summary = fetch_all_as_dict(summary_query, params)[0]

    numeric_fields = [
        "inventory_total_ore",
        "psi_allocated_tonnage",
        "diff_tonnage",
        "diff_tonnage_pct",
        "inventory_ni",
        "psi_ni",
        "diff_ni_pct",
        "inventory_fe",
        "psi_fe",
        "diff_fe_pct",
        "inventory_mgo",
        "psi_mgo",
        "diff_mgo_pct",
        "inventory_sio2",
        "psi_sio2",
        "diff_sio2_pct",
        "inventory_sm",
        "psi_sm",
        "diff_sm_pct",
    ]

    sql_data = convert_numeric_fields(sql_data, numeric_fields)

    summary = convert_numeric_fields([summary], [
        "inventory_total_ore",
        "psi_allocated_tonnage",
        "diff_tonnage",
        "total_dome",
        "total_has_psi",
        "total_no_psi",

        "inventory_avg_ni",
        "inventory_avg_fe",
        "inventory_avg_mgo",
        "inventory_avg_sio2",
        "inventory_avg_sm",

        "psi_avg_ni",
        "psi_avg_fe",
        "psi_avg_mgo",
        "psi_avg_sio2",
        "psi_avg_sm",
    ])[0]

    return JsonResponse({
        "data": sql_data,
        "summary": summary,
        "pagination": {
            "more": len(sql_data) == per_page,
            "total_pages": (total_data // per_page) + (1 if total_data % per_page > 0 else 0),
            "current_page": page,
            "total_data": total_data,
        }
    })
