from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import calendar
from datetime import datetime
from django.db import connection
import json 
from datetime import datetime
from analytics.services.iup_filter import build_iup_clause

def min_to_hour(m):
    return round((m or 0) / 60, 2)
from django.http import JsonResponse
from django.db import connection
import calendar
from datetime import datetime, timedelta


def kpi_monitoring(request):
    iup_filter = request.GET.get("iup_id")
    date_start = request.GET.get("date_start")
    date_end = request.GET.get("date_end")

    if not date_start or not date_end:
        return JsonResponse({"error": "date_start dan date_end wajib diisi"}, status=400)

    try:
        start_dt = datetime.strptime(date_start, "%Y-%m-%d")
        end_dt = datetime.strptime(date_end, "%Y-%m-%d")

        if end_dt < start_dt:
            return JsonResponse({
                "error": "date_end tidak boleh lebih kecil dari date_start"
            }, status=400)

        if (end_dt - start_dt).days > 31:
            return JsonResponse({
                "error": "Filter maksimal 1 bulan"
            }, status=400)

    except Exception:
        return JsonResponse({
            "error": "Format tanggal harus YYYY-MM-DD"
        }, status=400)
    
    try:
        query = """
            SELECT
                h.date,
                u.unit_vendor AS unit,
                u.unit_code,
                TRIM(c.category) AS category,

                ROUND(COALESCE(SUM(d.duration_min), 0)::numeric / 60, 2) AS total_hour,

                ROUND(
                    (1440 - COALESCE(SUM(d.duration_min), 0))::numeric / 60,
                    2
                ) AS missing_hour,

                CASE
                    WHEN COALESCE(SUM(d.duration_min), 0) = 1440 THEN 'Complete'
                    WHEN COALESCE(SUM(d.duration_min), 0) < 1440 THEN 'Incomplete'
                    ELSE 'Over'
                END AS status

            FROM mining_hm_unit h
            LEFT JOIN master_units u ON u.id = h.unit_id
            LEFT JOIN master_units_categories c ON c.id = u.id_category
            LEFT JOIN mining_hm_unit_detail d ON d.hm_unit_id = h.id
            WHERE h.date BETWEEN %s AND %s
        """

        params = [date_start, date_end]

        iup_clause, iup_params = build_iup_clause(iup_filter, "h")
        query += iup_clause
        params.extend(iup_params)

        query += """
            GROUP BY
                h.date,
                u.unit_vendor,
                u.unit_code,
                TRIM(c.category)

            HAVING COALESCE(SUM(d.duration_min), 0) <> 1440

            ORDER BY
                h.date DESC,
                u.unit_vendor,
                u.unit_code
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        data = []
        for r in rows:
            data.append({
                "date": r[0].strftime("%Y-%m-%d") if r[0] else None,
                "unit": r[1],
                "unit_code": r[2],
                "category": r[3],
                "total_hour": float(r[4] or 0),
                "missing_hour": float(r[5] or 0),
                "status": r[6],
            })

        return JsonResponse({
            "success": True,
            "date_start": date_start,
            "date_end": date_end,
            "data": data
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)