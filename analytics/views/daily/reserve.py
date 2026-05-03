# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
logger = logging.getLogger(__name__) 
import json
from analytics.services.iup_filter import build_iup_clause


class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):
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


def build_summary_query(where_reserve: str, where_prod: str, where_barge: str) -> str:
    return f"""
        WITH base AS (
            SELECT
                COALESCE(SUM(r.tonnage), 0) AS reserve_awal
            FROM mining_reserve r
            {where_reserve}
        ),
        prod AS (
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN mp.nama_material IN ('LIM', 'SAP') THEN mp.tonnage
                        ELSE 0
                    END
                ), 0) AS prod_ton
            FROM view_mining_productions mp
            {where_prod}
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


def get_reserve_summary_daily(request):
    try:
        iup_filter = request.GET.get("iup_id")
        filter_date = request.GET.get("filter_date")

        where_reserve = "WHERE 1=1"
        where_prod = "WHERE 1=1"
        where_barge = "WHERE s.status_barging = 'Complete'"
        params = []

        where_prod += " AND mp.date_production <= %s"
        where_barge += " AND s.date_barge_out <= %s"
        params += [filter_date, filter_date]

        r_iup_clause, r_iup_params = build_iup_clause(iup_filter, "r")
        mp_iup_clause, mp_iup_params = build_iup_clause(iup_filter, "mp")
        s_iup_clause, s_iup_params = build_iup_clause(iup_filter, "s")

        where_reserve += r_iup_clause
        where_prod += mp_iup_clause
        where_barge += s_iup_clause

        params += r_iup_params + mp_iup_params + s_iup_params

        query = build_summary_query(where_reserve, where_prod, where_barge)

        expected = query.count("%s")
        if expected != len(params):
            logger.warning(f"Param mismatch: query expects {expected}, got {len(params)}")
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

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({'error': 'Database error'}, status=500)
    except Exception as e:
        logger.exception("Unexpected error in get_reserve_summary")
        return JsonResponse({'error': str(e)}, status=500)