from datetime import datetime
from django.http import JsonResponse
from django.db import connection
from datetime import datetime, timedelta,date
import pandas as pd

def chart_tat_roa(request):
    params = []
    conditions = ["roa_order = 'Yes'"]

    start_date = request.GET.get('startDate')
    end_date   = request.GET.get('endDate')
    iup_filter = request.GET.get("iup_filter") or request.GET.get("iup_id")

    # DATE FILTER
    if start_date and end_date:
        conditions.append("tgl_produksi BETWEEN %s AND %s")
        params.extend([start_date, end_date])
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        conditions.append("tgl_produksi BETWEEN %s AND %s")
        params.extend([monday, today])

    # IUP FILTER (SIMPLE)
    if iup_filter not in (None, "", "null", "undefined"):
        conditions.append("iup_id = %s")
        params.append(iup_filter)

    # WHERE
    where_clause = "WHERE " + " AND ".join(conditions)

    # QUERY
    query = f"""
        SELECT 
            tgl_produksi,
            COUNT(DISTINCT sample_number) AS jml_roa,
            COUNT(DISTINCT CASE WHEN roa_remark = 'OnTime' THEN sample_number END) AS on_tat,
            COUNT(DISTINCT CASE WHEN roa_remark = 'Late' THEN sample_number END) AS over_tat,
            COUNT(DISTINCT CASE WHEN tat_roa IS NOT NULL THEN sample_number END) AS total_released,
            COUNT(DISTINCT CASE WHEN tat_roa IS NULL THEN sample_number END) AS not_released,
            COALESCE(
                ROUND(AVG(EXTRACT(EPOCH FROM release_roa - delivery))/3600, 2),
                0
            ) AS avg_hours,
            192 AS limit_hours
        FROM view_laboratory_performance_tat
        {where_clause}
        GROUP BY tgl_produksi
        ORDER BY tgl_produksi ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=[
        'tgl', 'order', 'on_tat', 'over_tat',
        'total_released', 'not_released',
        'avg_hours', 'limit_hours'
    ])

    if df.empty:
        return JsonResponse({
            "labels": [],
            "series": []
        })


    # RESPONSE (RAW)
    return JsonResponse({
        "labels": df['tgl'].astype(str).tolist(),
        "series": [
            {
                "name": "Samples",
                "type": "bar",
                "data": df['order'].tolist()
            },
            {
                "name": "TAT ROA",
                "type": "line",
                "data": df['avg_hours'].tolist()
            },
            {
                "name": "TAT Limit",
                "type": "line",
                "data": df['limit_hours'].tolist()
            }
        ],
        "detail": df.to_dict(orient="records")
    })


def get_data_roa_by_range(request):
    start_date = request.GET.get('startDate')
    end_date   = request.GET.get('endDate')
    iup_filter = request.GET.get("iup_filter") or request.GET.get("iup_id")

    sql_query = """
        SELECT 
            tgl_produksi,
            roa_order,
            COUNT(DISTINCT CASE WHEN roa_order = 'Yes' THEN sample_number END) AS jml_roa,
            COUNT(DISTINCT CASE WHEN roa_order = 'Yes' AND roa_remark = 'OnTime' AND tat_roa IS NOT NULL THEN sample_number END) AS released_on_tat,
            COUNT(DISTINCT CASE WHEN roa_order = 'Yes' AND roa_remark = 'Late' AND tat_roa IS NOT NULL THEN sample_number END) AS released_over_tat,
            COUNT(DISTINCT CASE WHEN roa_order = 'Yes' AND tat_roa IS NOT NULL THEN sample_number END) AS total_released,
            COUNT(DISTINCT CASE WHEN roa_order = 'Yes' AND tat_roa IS NULL THEN sample_number END) AS not_released,
            COALESCE(
                TO_CHAR(
                    INTERVAL '1 second' * ROUND(AVG(EXTRACT(EPOCH FROM release_roa - delivery))),
                    'HH24:MI:SS'
                ),
                '00:00:00'
            ) AS average_time,
            '192:00:00' AS time_limit
        FROM view_laboratory_performance_tat
        WHERE roa_order = 'Yes'
    """

    params = []

    if start_date and end_date:
        sql_query += " AND tgl_produksi BETWEEN %s AND %s "
        params.extend([start_date, end_date])
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sql_query += " AND tgl_produksi BETWEEN %s AND %s "
        params.extend([monday, today])

    if iup_filter not in (None, "", "null", "undefined"):
        sql_query += " AND iup_id = %s "
        params.append(iup_filter)

    sql_query += """
        GROUP BY tgl_produksi, roa_order
        ORDER BY tgl_produksi ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    for row in sql_data:
        if isinstance(row['tgl_produksi'], (datetime, date)):
            row['tgl_produksi'] = row['tgl_produksi'].strftime('%Y-%m-%d')

    return JsonResponse({'data': sql_data})

# MRAL Order :
def chart_tat_mral(request):
    params = []
    conditions = ["mral_order = 'Yes'"]

    start_date = request.GET.get('startDate')
    end_date   = request.GET.get('endDate')
    iup_filter = request.GET.get("iup_filter") or request.GET.get("iup_id")

    # DATE FILTER
    if start_date and end_date:
        conditions.append("tgl_produksi BETWEEN %s AND %s")
        params.extend([start_date, end_date])
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        conditions.append("tgl_produksi BETWEEN %s AND %s")
        params.extend([monday, today])

    # IUP FILTER (SIMPLE)
    if iup_filter not in (None, "", "null", "undefined"):
        conditions.append("iup_id = %s")
        params.append(iup_filter)

    # WHERE
    where_clause = "WHERE " + " AND ".join(conditions)

    # QUERY
    query = f"""
        SELECT 
            tgl_produksi,
            COUNT(DISTINCT sample_number) AS jml_roa,
            COUNT(DISTINCT CASE WHEN mral_remark = 'OnTime' THEN sample_number END) AS on_tat,
            COUNT(DISTINCT CASE WHEN mral_remark = 'Late' THEN sample_number END) AS over_tat,
            COUNT(DISTINCT CASE WHEN tat_roa IS NOT NULL THEN sample_number END) AS total_released,
            COUNT(DISTINCT CASE WHEN tat_roa IS NULL THEN sample_number END) AS not_released,
            COALESCE(
                    TO_CHAR(
                        INTERVAL '1 second' * ROUND(AVG(EXTRACT(EPOCH FROM release_mral - delivery))),
                        'HH24:MI:SS'
                    ),
                    '00:00:00'
                ) AS average_time,
                '03:00:00' AS limit_hours
        FROM view_laboratory_performance_tat
        {where_clause}
        GROUP BY tgl_produksi
        ORDER BY tgl_produksi ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=[
        'tgl', 'order', 'on_tat', 'over_tat',
        'total_released', 'not_released',
        'avg_hours', 'limit_hours'
    ])

    if df.empty:
        return JsonResponse({
            "labels": [],
            "series": []
        })


    # RESPONSE (RAW)
    return JsonResponse({
        "labels": df['tgl'].astype(str).tolist(),
        "series": [
            {
                "name": "Samples",
                "type": "bar",
                "data": df['order'].tolist()
            },
            {
                "name": "TAT ROA",
                "type": "line",
                "data": df['avg_hours'].tolist()
            },
            {
                "name": "TAT Limit",
                "type": "line",
                "data": df['limit_hours'].tolist()
            }
        ],
        "detail": df.to_dict(orient="records")
    })


def get_data_mral_by_range(request):
    start_date = request.GET.get('startDate')
    end_date   = request.GET.get('endDate')
    iup_filter = request.GET.get("iup_filter") or request.GET.get("iup_id")

    sql_query = """
        SELECT 
            tgl_produksi,
            mral_order,
            COUNT(DISTINCT CASE WHEN mral_order = 'Yes' THEN sample_number END) AS jml_roa,
            COUNT(DISTINCT CASE WHEN mral_order = 'Yes' AND roa_remark = 'OnTime' AND tat_roa IS NOT NULL THEN sample_number END) AS released_on_tat,
            COUNT(DISTINCT CASE WHEN mral_order = 'Yes' AND roa_remark = 'Late' AND tat_roa IS NOT NULL THEN sample_number END) AS released_over_tat,
            COUNT(DISTINCT CASE WHEN mral_order = 'Yes' AND tat_roa IS NOT NULL THEN sample_number END) AS total_released,
            COUNT(DISTINCT CASE WHEN mral_order = 'Yes' AND tat_roa IS NULL THEN sample_number END) AS not_released,
            COALESCE(
                TO_CHAR(
                    INTERVAL '1 second' * ROUND(AVG(EXTRACT(EPOCH FROM release_roa - delivery))),
                    'HH24:MI:SS'
                ),
                '00:00:00'
                ) AS average_time,
            '105:00:00' AS time_limit
        FROM view_laboratory_performance_tat
        WHERE mral_order = 'Yes'
    """

    params = []

    if start_date and end_date:
        sql_query += " AND tgl_produksi BETWEEN %s AND %s "
        params.extend([start_date, end_date])
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sql_query += " AND tgl_produksi BETWEEN %s AND %s "
        params.extend([monday, today])

    if iup_filter not in (None, "", "null", "undefined"):
        sql_query += " AND iup_id = %s "
        params.append(iup_filter)

    sql_query += """
        GROUP BY tgl_produksi, mral_order
        ORDER BY tgl_produksi ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        columns = [col[0] for col in cursor.description]
        sql_data = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    for row in sql_data:
        if isinstance(row['tgl_produksi'], (datetime, date)):
            row['tgl_produksi'] = row['tgl_produksi'].strftime('%Y-%m-%d')

    return JsonResponse({'data': sql_data})