# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import json
logger = logging.getLogger(__name__)
from analytics.services.iup_filter import build_iup_clause

class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def to_float1(value):
    try:
        return round(float(value or 0), 1)
    except Exception:
        return 0.0

def dictfetchone(cursor):
    desc = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(desc, row)) if row else {}

# Query Builder
def build_summary_query(where_clause: str, where_barge: str) -> str:
    return f"""
        WITH base AS (
            SELECT COALESCE(SUM(r.tonnage), 0) AS reserve_awal
            FROM mining_reserve r
        ),
        prod AS (
            SELECT
                COALESCE(SUM(
                    CASE WHEN nama_material IN ('LIM', 'SAP') THEN tonnage ELSE 0 END
                ), 0) AS prod_ton
            FROM view_geology_ore_production
            {where_clause}
        ),
        sales AS (
            SELECT
                COALESCE(SUM(s.tonnage), 0) AS sales_ton
            FROM selling_barging s
            {where_barge}
        )
        SELECT
            base.reserve_awal,
            prod.prod_ton,
            sales.sales_ton,
            (base.reserve_awal - prod.prod_ton - sales.sales_ton) AS remaining_reserve,
            CASE
                WHEN base.reserve_awal = 0 THEN 0
                ELSE (prod.prod_ton / base.reserve_awal) * 100
            END AS percent_mined,
            CASE
                WHEN base.reserve_awal = 0 THEN 0
                ELSE (sales.sales_ton / base.reserve_awal) * 100
            END AS percent_sold
        FROM base, prod, sales;
    """

# Main Function
def get_reserve_summary(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        where_clause = "WHERE 1=1"
        where_barge  = "WHERE status_barging = 'Complete'"

        prod_params = []
        sell_params = []

        # FILTER IUP
        iup_prod_clause, iup_prod_params = build_iup_clause(iup_filter, "r")
        iup_sell_clause, iup_sell_params = build_iup_clause(iup_filter, "s")

        # view_geology_ore_production tidak pakai alias r
        where_clause += iup_prod_clause.replace("r.", "")
        where_barge  += iup_sell_clause

        prod_params += iup_prod_params
        sell_params += iup_sell_params

        # FILTER DATE
        if filter_type == "daily" and filter_date:
            where_clause += " AND tgl_production <= %s"
            where_barge  += " AND date_barge_out <= %s"
            prod_params += [filter_date]
            sell_params += [filter_date]

        elif filter_type == "range" and date_end:
            where_clause += " AND tgl_production <= %s"
            where_barge  += " AND date_barge_out <= %s"
            prod_params += [date_end]
            sell_params += [date_end]

        elif filter_type == "weekly" and week:
            where_clause += """
                AND tgl_production < (
                    DATE_TRUNC('week', TO_DATE(%s || '-1', 'IYYY-IW-ID')) + INTERVAL '7 day'
                )
            """
            where_barge += """
                AND date_barge_out < (
                    DATE_TRUNC('week', TO_DATE(%s || '-1', 'IYYY-IW-ID')) + INTERVAL '7 day'
                )
            """
            prod_params += [week]
            sell_params += [week]

        elif filter_type == "monthly" and year and month:
            where_clause += """
                AND (
                    EXTRACT(YEAR FROM tgl_production) < %s
                    OR (
                        EXTRACT(YEAR FROM tgl_production) = %s
                        AND EXTRACT(MONTH FROM tgl_production) <= %s
                    )
                )
            """
            where_barge += """
                AND (
                    EXTRACT(YEAR FROM date_barge_out) < %s
                    OR (
                        EXTRACT(YEAR FROM date_barge_out) = %s
                        AND EXTRACT(MONTH FROM date_barge_out) <= %s
                    )
                )
            """
            prod_params += [year, year, month]
            sell_params += [year, year, month]

        elif filter_type == "yearly" and year:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) <= %s"
            where_barge  += " AND EXTRACT(YEAR FROM date_barge_out) <= %s"
            prod_params += [year]
            sell_params += [year]

        elif filter_type == "all":
            pass

        else:
            return JsonResponse({"error": "Invalid filter type"}, status=400)

        query = build_summary_query(where_clause, where_barge)

        # urutan harus sesuai query: prod dulu, baru sales
        params = prod_params + sell_params

        expected = query.count("%s")
        if expected != len(params):
            logger.warning(f"Param mismatch: expected {expected}, got {len(params)}")
            logger.warning(f"Params: {params}")

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = dictfetchone(cursor)

        return JsonResponse({
            "reserve_ton": to_float1(row["reserve_awal"]),
            "prod_ton": to_float1(row["prod_ton"]),
            "sales_ton": to_float1(row["sales_ton"]),
            "remaining_reserve": to_float1(row["remaining_reserve"]),
            "percent_mined": round(to_float1(row["percent_mined"]), 2),
            "percent_sold": round(to_float1(row["percent_sold"]), 2),
        })

    except Exception as e:
        logger.exception("Error reserve summary")
        return JsonResponse({"error": str(e)}, status=500)