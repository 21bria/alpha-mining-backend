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
 
def build_inventory_raw_filters(request, forced_material=None):
    iup_filter      = request.GET.get("iup_id")
    material_filter = forced_material or request.GET.get("material")
    area_filter     = request.GET.get("areaFilter")
    point_filter    = request.GET.getlist("pointFilter")
    cut_date        = request.GET.get("date") or request.GET.get("cut_date")

    if not iup_filter:
        return None, None, None, JsonResponse({"error": "iup_id wajib diisi"}, status=400)

    if not cut_date:
        return None, None, None, JsonResponse({"error": "cut_date wajib diisi"}, status=400)

    prod_conditions = [
        "p.status_dome != 'Finished'",
        "p.direct = 'No'",
        "p.tgl_production <= %s",
        "p.iup_id = %s",
    ]
    sell_conditions = [
        "s.date_barge_out <= %s",
        "s.status_barging = 'Complete'",
        "s.iup_id = %s",
    ]

    prod_params = [cut_date, iup_filter]
    sell_params = [cut_date, iup_filter]

    sale_mapping = {
        "LIM": "HPAL",
        "SAP": "RKEF",
    }

    if material_filter not in [None, ""]:
        mapped_sale = sale_mapping.get(material_filter, material_filter)
        prod_conditions.append("p.sale_adjust = %s")
        prod_params.append(mapped_sale)

    if area_filter not in [None, ""]:
        prod_conditions.append("TRIM(p.stockpile) = %s")
        prod_params.append(area_filter)

        sell_conditions.append("TRIM(s.stockpile) = %s")
        sell_params.append(area_filter)

    if point_filter:
        placeholders = ", ".join(["%s"] * len(point_filter))

        prod_conditions.append(f"TRIM(p.pile_id) IN ({placeholders})")
        prod_params.extend(point_filter)

        sell_conditions.append(f"TRIM(s.dome) IN ({placeholders})")
        sell_params.extend(point_filter)

    prod_where = "WHERE " + " AND ".join(prod_conditions)
    sell_where = "WHERE " + " AND ".join(sell_conditions)

    return prod_where, sell_where, prod_params + sell_params, None

# Stockpile
# Management Inventory Summary
def get_inventory_management(request):
    prod_where, sell_where, params, error_response = build_inventory_raw_filters(request)
    if error_response:
        return error_response

    cut_date = request.GET.get("date") or request.GET.get("cut_date")

    selling_case = """
        CASE
            WHEN p.nama_material = 'LIM' AND s.nama_material = 'SAP' THEN s.tonnage
            WHEN p.nama_material = 'SAP' AND s.nama_material = 'LIM' THEN s.tonnage
            WHEN p.nama_material = s.nama_material THEN s.tonnage
            ELSE 0
        END
    """

    base_query = f"""
        WITH prod AS (
            SELECT
                p.iup_id,
                TRIM(p.stockpile) AS stockpile,
                TRIM(p.pile_id) AS pile_id,
                TRIM(p.nama_material) AS nama_material,
                SUM(p.tonnage) AS total_ore,
                SUM(CASE WHEN p.roa_ni IS NOT NULL AND p.sample_number IS NOT NULL THEN p.tonnage ELSE 0 END) AS released,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_ni) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_ni IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS ni,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_co) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_co IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS co,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_al2o3) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_al2o3 IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS al2o3,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_cao) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_cao IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS cao,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_cr2o3) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_cr2o3 IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS cr2o3,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_fe) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_fe IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS fe,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_mgo) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_mgo IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS mgo,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_sio2) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_sio2 IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS sio2,
                ROUND(COALESCE(SUM(p.tonnage * p.roa_mc) / NULLIF(SUM(CASE WHEN p.sample_number IS NOT NULL AND p.roa_mc IS NOT NULL THEN p.tonnage ELSE 0 END), 0), 0)::numeric, 2) AS mc
            FROM view_geology_ore_details_roa p
            {prod_where}
            GROUP BY p.iup_id, p.stockpile, p.pile_id, p.nama_material
        ),

        sell AS (
            SELECT
                s.iup_id,
                TRIM(s.stockpile) AS stockpile,
                TRIM(s.dome) AS pile_id,
                TRIM(s.material) AS nama_material,
                SUM(s.tonnage) AS tonnage
            FROM view_selling_details s
            {sell_where}
            GROUP BY s.iup_id, s.stockpile, s.dome, s.material
        ),

        dome_calc AS (
            SELECT
                p.iup_id,
                p.stockpile,
                p.pile_id,
                p.nama_material,
                p.total_ore,
                p.released,
                COALESCE(SUM({selling_case}), 0) AS total_selling,
                p.total_ore - COALESCE(SUM({selling_case}), 0) AS balance,
                p.ni, p.co, p.al2o3, p.cao, p.cr2o3,
                p.fe, p.mgo, p.sio2, p.mc
            FROM prod p
            LEFT JOIN sell s
                ON s.iup_id = p.iup_id
               AND s.stockpile = p.stockpile
               AND s.pile_id = p.pile_id
            GROUP BY
                p.iup_id, p.stockpile, p.pile_id, p.nama_material,
                p.total_ore, p.released,
                p.ni, p.co, p.al2o3, p.cao, p.cr2o3,
                p.fe, p.mgo, p.sio2, p.mc
        ),

        material_agg AS (
            SELECT
                nama_material AS material,
                ROUND(SUM(balance)::numeric, 2) AS balance,
                ROUND(COALESCE(SUM(balance * ni) / NULLIF(SUM(balance), 0), 0)::numeric, 2) AS ni,
                ROUND(COALESCE(SUM(balance * co) / NULLIF(SUM(balance), 0), 0)::numeric, 2) AS co,
                ROUND(COALESCE(SUM(balance * fe) / NULLIF(SUM(balance), 0), 0)::numeric, 2) AS fe,
                ROUND(COALESCE(SUM(balance * mgo) / NULLIF(SUM(balance), 0), 0)::numeric, 2) AS mgo,
                ROUND(COALESCE(SUM(balance * sio2) / NULLIF(SUM(balance), 0), 0)::numeric, 2) AS sio2,
                ROUND(COALESCE(SUM(balance * mc) / NULLIF(SUM(balance), 0), 0)::numeric, 2) AS mc
            FROM dome_calc
            GROUP BY nama_material
        ),
        summary AS (
                SELECT
                    ROUND(COALESCE(SUM(balance),0)::numeric,2) AS total_balance,
                    COUNT(DISTINCT stockpile) AS stockpile_count,
                    ROUND(
                        COALESCE(
                            SUM(balance * ni) / NULLIF(SUM(balance),0),
                        0)::numeric,
                    2) AS avg_ni,

                    ROUND(
                        COALESCE(
                            SUM(balance * fe) / NULLIF(SUM(balance),0),
                        0)::numeric,
                    2) AS avg_fe,

                    ROUND(
                        COALESCE(
                            SUM(balance * mc) / NULLIF(SUM(balance),0),
                        0)::numeric,
                    2) AS avg_mc

                FROM dome_calc
            )
        SELECT
            (SELECT row_to_json(summary) FROM summary) AS summary,
            (SELECT COALESCE(json_agg(material_agg), '[]'::json) FROM material_agg) AS materials
    """

    with connection.cursor() as cursor:
        cursor.execute(base_query, params)
        row = cursor.fetchone()

    summary = row[0] or {}
    materials = row[1] or []

    return JsonResponse({
        "cut_date": cut_date,
        "summary": summary,
        "materials": materials,
    })