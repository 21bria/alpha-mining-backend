import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
from analytics.services.iup_filter import build_iup_clause
logger = logging.getLogger(__name__)


def to_float1(v):
    return round(float(v or 0), 1)

# Card Summary
def build_summary_query(where_clause: str) -> str:
    return f"""
        SELECT 
            COALESCE(
                ROUND(
                    SUM(CASE WHEN vsd.material IN ('LIM', 'SAP') THEN vsd.tonnage ELSE 0 END)::numeric,
                    2
                ),
                0
            ) AS total,
            COALESCE(
                ROUND(
                    SUM(CASE WHEN vsd.material = 'LIM' THEN vsd.tonnage ELSE 0 END)::numeric,
                    2
                ),
                0
            ) AS total_lim,
            COALESCE(
                ROUND(
                    SUM(CASE WHEN vsd.material = 'SAP' THEN vsd.tonnage ELSE 0 END)::numeric,
                    2
                ),
                0
            ) AS total_sap
        FROM view_selling_details vsd
        {where_clause}
    """

def get_barging_weekly(request):
    try:
        iup_filter   = request.GET.get("iup_id") or request.GET.get("iup_filter")
        period_start = request.GET.get("period_start")
        period_end   = request.GET.get("period_end")

        where_clause = "WHERE 1=1"
        params = []

        # pakai alias
        iup_clause, iup_params = build_iup_clause(iup_filter, "vsd")

        # apply iup filter
        where_clause += iup_clause
        params += iup_params

        # filter periode
        where_clause += " AND vsd.date_hauling BETWEEN %s AND %s"
        params += [period_start, period_end]

    
        query = build_summary_query(where_clause)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        return JsonResponse({
            "total_barging" : to_float1(row[0]),
            "total_lim"     : to_float1(row[1]),
            "total_sap"     : to_float1(row[2]),
        })

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in get_barging_weekly")
        