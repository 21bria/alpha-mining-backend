# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import calendar
from datetime import datetime, timedelta
from analytics.services.iup_filter import build_iup_clause
logger = logging.getLogger(__name__)


def to_float1(v):
    return round(float(v or 0), 1)

## Card Summary
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

def get_barging_summary(request):
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
        params = []

        # pakai alias
        iup_clause, iup_params = build_iup_clause(iup_filter, "vsd")

        # apply iup filter
        where_clause += iup_clause
        params += iup_params

        # filter periode
        if filter_type == "daily" and filter_date:
            where_clause += " AND vsd.date_hauling = %s"
            params += [filter_date]

        elif filter_type == "range" and date_start and date_end:
            where_clause += " AND vsd.date_hauling BETWEEN %s AND %s"
            params += [date_start, date_end]

        elif filter_type == "weekly" and week:
            where_clause += " AND TO_CHAR(vsd.date_hauling, 'IYYY-IW') = %s"
            params += [week]

        elif filter_type == "monthly" and year and month:
            where_clause += """
                AND EXTRACT(YEAR FROM vsd.date_hauling) = %s
                AND EXTRACT(MONTH FROM vsd.date_hauling) = %s
            """
            params += [year, month]

        elif filter_type == "yearly" and year:
            where_clause += " AND EXTRACT(YEAR FROM vsd.date_hauling) = %s"
            params += [year]

        elif filter_type == "all" or not filter_type:
            pass

        else:
            return JsonResponse({"error": "Invalid filter type"}, status=400)

        query = build_summary_query(where_clause)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        return JsonResponse({
            "total_ore": to_float1(row[0]),
            "total_lim": to_float1(row[1]),
            "total_sap": to_float1(row[2]),
        })

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in get_barging_summary_group")
        return JsonResponse({"error": str(e)}, status=500)
    
# Chart Barging
def get_chart_barging(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        iup_clause_s, iup_params_s = build_iup_clause(iup_filter, "s")
        iup_clause_p, iup_params_p = build_iup_clause(iup_filter, "p")

        details = []
        if filter_type == "daily" and filter_date:
            query = f"""
                WITH working_hours AS (
                    SELECT
                        hour_label,
                        CASE
                            WHEN hour_label >= 7 THEN hour_label
                            ELSE hour_label + 24
                        END AS sort_order
                    FROM generate_series(0, 23) AS hour_label
                ),
                actual AS (
                    SELECT
                        s.iup_id,
                        EXTRACT(HOUR FROM s.time_hauling)::int AS hour_label,
                        SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END) AS actual_lim,
                        SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END) AS actual_sap,
                        SUM(s.tonnage) AS actual_total
                    FROM selling_barging s
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    WHERE s.date_hauling::date = %s::date
                    {iup_clause_s}
                    GROUP BY s.iup_id, EXTRACT(HOUR FROM s.time_hauling)
                ),
                detail AS (
                    SELECT
                        s.iup_id,
                        EXTRACT(HOUR FROM s.time_hauling)::int AS hour_label,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni AS ni_plan,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    LEFT JOIN master_selling_code msc ON msc.code = s.code_lot
                    WHERE s.date_hauling::date = %s::date
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        EXTRACT(HOUR FROM s.time_hauling),
                        mb.barge_code,
                        s.code_lot,
                        msc.ni
                ),
                plan AS (
                    SELECT
                        p.iup_id,
                        p.plan_date,
                        p.barge_code,
                        MAX(p.tugboat_name) AS tugboat_name,
                        ROUND(COALESCE(SUM(p.tonnage_plan), 0)::numeric, 2) AS tonnage_plan,
                        MAX(p.no_plan) AS no_plan
                    FROM selling_plan_barging p
                    WHERE p.plan_date = %s::date
                    {iup_clause_p}
                    GROUP BY
                        p.iup_id,
                        p.plan_date,
                        p.barge_code
                ),
                plan_daily AS (
                    SELECT
                        ROUND(COALESCE(SUM(tonnage_plan), 0)::numeric, 2) AS plan_total_daily,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'barge_code', p.barge_code,
                                    'tugboat_name', p.tugboat_name,
                                    'tonnage_plan', p.tonnage_plan,
                                    'no_plan', p.no_plan
                                )
                                ORDER BY p.barge_code
                            ),
                            '[]'::json
                        ) AS summary_plan_by_barge
                    FROM plan p
                )
                SELECT
                    wh.hour_label AS label,
                    ROUND(COALESCE(SUM(a.actual_total), 0), 2) AS actual_total,
                    ROUND(COALESCE(SUM(a.actual_lim), 0), 2) AS actual_lim,
                    ROUND(COALESCE(SUM(a.actual_sap), 0), 2) AS actual_sap,
                    pd.plan_total_daily,
                    pd.summary_plan_by_barge,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'code_lot', d.code_lot,
                                'ni_plan', d.ni_plan,
                                'total', d.total,
                                'lim', d.lim,
                                'sap', d.sap
                            )
                            ORDER BY d.barge_code, d.code_lot
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS summary_by_barge
                FROM working_hours wh
                LEFT JOIN actual a ON a.hour_label = wh.hour_label
                LEFT JOIN detail d ON d.hour_label = wh.hour_label
                CROSS JOIN plan_daily pd
                GROUP BY
                    wh.hour_label,
                    wh.sort_order,
                    pd.plan_total_daily,
                    pd.summary_plan_by_barge
                ORDER BY wh.sort_order;
            """
            params = (
                [filter_date]
                + iup_params_s
                + [filter_date]
                + iup_params_s
                + [filter_date]
                + iup_params_p
            )
        elif filter_type == "range" and date_start and date_end:
            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                actual AS (
                    SELECT
                        s.iup_id,
                        s.date_hauling::date AS date,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total
                    FROM selling_barging s
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    WHERE s.date_hauling BETWEEN %s AND %s
                    {iup_clause_s}
                    GROUP BY s.iup_id, s.date_hauling::date
                ),
                detail AS (
                    SELECT
                        s.iup_id,
                        s.date_hauling::date AS date,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni AS ni_plan,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    LEFT JOIN master_selling_code msc ON msc.code = s.code_lot
                    WHERE s.date_hauling BETWEEN %s AND %s
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        s.date_hauling::date,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni
                ),
                plan AS (
                    SELECT
                        p.iup_id,
                        p.plan_date AS date,
                        p.barge_code,
                        MAX(p.tugboat_name) AS tugboat_name,
                        ROUND(COALESCE(SUM(p.tonnage_plan), 0)::numeric, 2) AS tonnage_plan,
                        MAX(p.no_plan) AS no_plan
                    FROM selling_plan_barging p
                    WHERE p.plan_date BETWEEN %s AND %s
                    {iup_clause_p}
                    GROUP BY p.iup_id, p.plan_date, p.barge_code
                )
                SELECT
                    TO_CHAR(tanggal.date, 'YYYY-MM-DD') AS label,
                    ROUND(COALESCE(SUM(d.total), 0), 2) AS actual_total,
                    ROUND(COALESCE(SUM(d.lim), 0), 2) AS actual_lim,
                    ROUND(COALESCE(SUM(d.sap), 0), 2) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'code_lot', d.code_lot,
                                'ni_plan', d.ni_plan,
                                'tonnage_plan', p.tonnage_plan,
                                'no_plan', p.no_plan,
                                'tugboat_name', p.tugboat_name,
                                'total', d.total,
                                'lim', d.lim,
                                'sap', d.sap,
                                'variance', ROUND((COALESCE(d.total,0) - COALESCE(p.tonnage_plan,0))::numeric, 2)
                            )
                            ORDER BY d.barge_code, d.code_lot
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS summary_by_barge
                FROM tanggal
                LEFT JOIN detail d ON tanggal.date = d.date
                LEFT JOIN plan p 
                    ON p.date = d.date 
                    AND p.barge_code = d.barge_code
                    AND p.iup_id = d.iup_id
                GROUP BY tanggal.date
                ORDER BY tanggal.date;
            """

            params = []
            params += [date_start, date_end]   # tanggal
            params += [date_start, date_end]   # actual
            params += iup_params_s
            params += [date_start, date_end]   # detail
            params += iup_params_s
            params += [date_start, date_end]   # plan
            params += iup_params_p

        elif filter_type == "weekly" and year and month and week:
            try:
                if "-" in str(week):
                    year_str, week_str = str(week).split("-")
                    year = int(year_str)
                    week = int(week_str)
                    start_date = datetime.strptime(f"{year}-W{week:02}-1", "%G-W%V-%u")
                    end_date = start_date + timedelta(days=6)
                else:
                    year = int(year)
                    month = int(month)
                    week = int(week)

                    if not (1 <= month <= 12):
                        return JsonResponse({"error": "Bulan tidak valid (1–12)"}, status=400)
                    if not (1 <= week <= 5):
                        return JsonResponse({"error": "Minggu tidak valid (1–5)"}, status=400)

                    first_day = datetime(year, month, 1)
                    start_date = first_day + timedelta(days=(week - 1) * 7)
                    end_date = start_date + timedelta(days=6)

                    if end_date.month != month:
                        next_month = datetime(year, month, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

            except Exception as e:
                return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                actual AS (
                    SELECT
                        s.iup_id,
                        s.date_hauling::date AS date,
                        SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END) AS lim,
                        SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END) AS sap,
                        SUM(s.tonnage) AS total
                    FROM selling_barging s
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    WHERE s.date_hauling BETWEEN %s AND %s
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        s.date_hauling::date
                ),
                combine AS (
                    SELECT
                        t.date,
                        TO_CHAR(t.date, 'FMDay') AS day_name,
                        COALESCE(SUM(a.lim), 0) AS lim,
                        COALESCE(SUM(a.sap), 0) AS sap,
                        COALESCE(SUM(a.total), 0) AS total
                    FROM tanggal t
                    LEFT JOIN actual a ON t.date = a.date
                    GROUP BY t.date
                ),
                detail AS (
                    SELECT
                        s.iup_id,
                        s.date_hauling::date AS date,
                        TO_CHAR(s.date_hauling, 'FMDay') AS day_name,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni AS ni_plan,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    LEFT JOIN master_selling_code msc ON msc.code = s.code_lot
                    WHERE s.date_hauling BETWEEN %s AND %s
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        s.date_hauling::date,
                        TO_CHAR(s.date_hauling, 'FMDay'),
                        mb.barge_code,
                        s.code_lot,
                        msc.ni
                ),
                plan AS (
                    SELECT
                        p.iup_id,
                        p.plan_date AS date,
                        p.barge_code,
                        MAX(p.tugboat_name) AS tugboat_name,
                        ROUND(COALESCE(SUM(p.tonnage_plan), 0)::numeric, 2) AS tonnage_plan,
                        MAX(p.no_plan) AS no_plan
                    FROM selling_plan_barging p
                    WHERE p.plan_date BETWEEN %s AND %s
                    {iup_clause_p}
                    GROUP BY
                        p.iup_id,
                        p.plan_date,
                        p.barge_code
                )
                SELECT
                    c.day_name AS label,
                    ROUND(COALESCE(c.total, 0)::numeric, 2) AS actual_total,
                    ROUND(COALESCE(c.lim, 0)::numeric, 2) AS actual_lim,
                    ROUND(COALESCE(c.sap, 0)::numeric, 2) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'code_lot', d.code_lot,
                                'ni_plan', d.ni_plan,
                                'tonnage_plan', p.tonnage_plan,
                                'no_plan', p.no_plan,
                                'tugboat_name', p.tugboat_name,
                                'total', d.total,
                                'lim', d.lim,
                                'sap', d.sap,
                                'variance', ROUND((COALESCE(d.total, 0) - COALESCE(p.tonnage_plan, 0))::numeric, 2)
                            )
                            ORDER BY d.barge_code, d.code_lot
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS summary_by_barge
                FROM combine c
                LEFT JOIN detail d
                    ON c.date = d.date
                LEFT JOIN plan p
                    ON p.date = d.date
                AND p.barge_code = d.barge_code
                AND p.iup_id = d.iup_id
                GROUP BY
                    c.date,
                    c.day_name,
                    c.total,
                    c.lim,
                    c.sap
                ORDER BY ARRAY_POSITION(
                    ARRAY['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
                    c.day_name
                );
            """
            params = (
                [start_str, end_str, start_str, end_str]
                + iup_params_s
                + [start_str, end_str]
                + iup_params_s
                + [start_str, end_str]
                + iup_params_p
            )

        elif filter_type == "monthly" and year and month:
            year = int(year)
            month = int(month)
            last_day = calendar.monthrange(year, month)[1]
            tgl_pertama = datetime(year, month, 1).date()
            tgl_terakhir = datetime(year, month, last_day).date()

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                detail AS (
                    SELECT
                        s.iup_id,
                        s.date_hauling::date AS date,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni AS ni_plan,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    LEFT JOIN master_selling_code msc ON msc.code = s.code_lot
                    WHERE s.date_hauling BETWEEN %s AND %s
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        s.date_hauling::date,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni
                ),
                plan AS (
                    SELECT
                        p.iup_id,
                        p.plan_date AS date,
                        p.barge_code,
                        MAX(p.tugboat_name) AS tugboat_name,
                        ROUND(COALESCE(SUM(p.tonnage_plan), 0)::numeric, 2) AS tonnage_plan,
                        MAX(p.no_plan) AS no_plan
                    FROM selling_plan_barging p
                    WHERE p.plan_date BETWEEN %s AND %s
                    {iup_clause_p}
                    GROUP BY
                        p.iup_id,
                        p.plan_date,
                        p.barge_code
                )
                SELECT
                    TO_CHAR(t.date, 'DD') AS label,
                    ROUND(COALESCE(SUM(d.total), 0), 2) AS actual_total,
                    ROUND(COALESCE(SUM(d.lim), 0), 2) AS actual_lim,
                    ROUND(COALESCE(SUM(d.sap), 0), 2) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'code_lot', d.code_lot,
                                'ni_plan', d.ni_plan,
                                'tonnage_plan', p.tonnage_plan,
                                'no_plan', p.no_plan,
                                'tugboat_name', p.tugboat_name,
                                'total', d.total,
                                'lim', d.lim,
                                'sap', d.sap,
                                'variance', ROUND((COALESCE(d.total, 0) - COALESCE(p.tonnage_plan, 0))::numeric, 2)
                            )
                            ORDER BY d.barge_code, d.code_lot
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS summary_by_barge
                FROM tanggal t
                LEFT JOIN detail d
                    ON t.date = d.date
                LEFT JOIN plan p
                    ON p.date = d.date
                AND p.barge_code = d.barge_code
                AND p.iup_id = d.iup_id
                GROUP BY t.date
                ORDER BY t.date;
            """
            params = (
                    [tgl_pertama, tgl_terakhir, tgl_pertama, tgl_terakhir]
                    + iup_params_s
                    + [tgl_pertama, tgl_terakhir]
                    + iup_params_p
                )

        elif filter_type == "yearly" and year:
            year = int(year)

            query = f"""
                WITH bulan AS (
                    SELECT generate_series(1, 12) AS month
                ),
                detail AS (
                    SELECT
                        s.iup_id,
                        EXTRACT(MONTH FROM s.date_hauling)::int AS month,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni AS ni_plan,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    LEFT JOIN master_selling_code msc ON msc.code = s.code_lot
                    WHERE EXTRACT(YEAR FROM s.date_hauling) = %s
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        EXTRACT(MONTH FROM s.date_hauling),
                        mb.barge_code,
                        s.code_lot,
                        msc.ni
                ),
                plan AS (
                    SELECT
                        p.iup_id,
                        EXTRACT(MONTH FROM p.plan_date)::int AS month,
                        p.barge_code,
                        MAX(p.tugboat_name) AS tugboat_name,
                        ROUND(COALESCE(SUM(p.tonnage_plan), 0)::numeric, 2) AS tonnage_plan,
                        MAX(p.no_plan) AS no_plan
                    FROM selling_plan_barging p
                    WHERE EXTRACT(YEAR FROM p.plan_date) = %s
                    {iup_clause_p}
                    GROUP BY
                        p.iup_id,
                        EXTRACT(MONTH FROM p.plan_date),
                        p.barge_code
                )
                SELECT
                    TO_CHAR(TO_DATE(bulan.month::text, 'MM'), 'Mon') AS label,
                    ROUND(COALESCE(SUM(d.total), 0), 2) AS actual_total,
                    ROUND(COALESCE(SUM(d.lim), 0), 2) AS actual_lim,
                    ROUND(COALESCE(SUM(d.sap), 0), 2) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'code_lot', d.code_lot,
                                'ni_plan', d.ni_plan,
                                'tonnage_plan', p.tonnage_plan,
                                'no_plan', p.no_plan,
                                'tugboat_name', p.tugboat_name,
                                'total', d.total,
                                'lim', d.lim,
                                'sap', d.sap,
                                'variance', ROUND((COALESCE(d.total, 0) - COALESCE(p.tonnage_plan, 0))::numeric, 2)
                            )
                            ORDER BY d.barge_code, d.code_lot
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS summary_by_barge
                FROM bulan
                LEFT JOIN detail d
                    ON bulan.month = d.month
                LEFT JOIN plan p
                    ON p.month = d.month
                AND p.barge_code = d.barge_code
                AND p.iup_id = d.iup_id
                GROUP BY bulan.month
                ORDER BY bulan.month;
            """

            params = [year] + iup_params_s + [year] + iup_params_p

        elif filter_type == "all":
            query = f"""
                WITH tahun AS (
                    SELECT DISTINCT EXTRACT(YEAR FROM s.date_hauling)::int AS year
                    FROM selling_barging s
                    WHERE s.status_barging = 'Complete'
                    {iup_clause_s}
                ),
                detail AS (
                    SELECT
                        s.iup_id,
                        EXTRACT(YEAR FROM s.date_hauling)::int AS year,
                        mb.barge_code,
                        s.code_lot,
                        msc.ni AS ni_plan,
                        ROUND(SUM(s.tonnage)::numeric, 2) AS total,
                        ROUND(SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END)::numeric, 2) AS lim,
                        ROUND(SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END)::numeric, 2) AS sap
                    FROM selling_barging s
                    LEFT JOIN master_barge mb ON mb.id = s.barge_code
                    LEFT JOIN master_materials m ON m.id = s.id_material
                    LEFT JOIN master_selling_code msc ON msc.code = s.code_lot
                    WHERE s.status_barging = 'Complete'
                    {iup_clause_s}
                    GROUP BY
                        s.iup_id,
                        EXTRACT(YEAR FROM s.date_hauling),
                        mb.barge_code,
                        s.code_lot,
                        msc.ni
                ),
                plan AS (
                    SELECT
                        p.iup_id,
                        EXTRACT(YEAR FROM p.plan_date)::int AS year,
                        p.barge_code,
                        MAX(p.tugboat_name) AS tugboat_name,
                        ROUND(COALESCE(SUM(p.tonnage_plan), 0)::numeric, 2) AS tonnage_plan,
                        MAX(p.no_plan) AS no_plan
                    FROM selling_plan_barging p
                    WHERE 1=1
                    {iup_clause_p}
                    GROUP BY
                        p.iup_id,
                        EXTRACT(YEAR FROM p.plan_date),
                        p.barge_code
                )
                SELECT
                    t.year::text AS label,
                    ROUND(COALESCE(SUM(d.total), 0)::numeric, 2) AS actual_total,
                    ROUND(COALESCE(SUM(d.lim), 0)::numeric, 2) AS actual_lim,
                    ROUND(COALESCE(SUM(d.sap), 0)::numeric, 2) AS actual_sap,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'barge_code', d.barge_code,
                                'code_lot', d.code_lot,
                                'ni_plan', d.ni_plan,
                                'tonnage_plan', p.tonnage_plan,
                                'no_plan', p.no_plan,
                                'tugboat_name', p.tugboat_name,
                                'total', d.total,
                                'lim', d.lim,
                                'sap', d.sap,
                                'variance', ROUND((COALESCE(d.total, 0) - COALESCE(p.tonnage_plan, 0))::numeric, 2)
                            )
                            ORDER BY d.barge_code, d.code_lot
                        ) FILTER (WHERE d.barge_code IS NOT NULL),
                        '[]'::json
                    ) AS summary_by_barge
                FROM tahun t
                LEFT JOIN detail d
                    ON t.year = d.year
                LEFT JOIN plan p
                    ON p.year = d.year
                AND p.barge_code = d.barge_code
                AND p.iup_id = d.iup_id
                GROUP BY t.year
                ORDER BY t.year;
            """
            params = iup_params_s + iup_params_s + iup_params_p

        else:
            return JsonResponse({'error': 'Invalid or incomplete filter parameters'}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        for row in results:
            label        = str(row[0])
            total_actual = float(row[1] or 0)
            lim_value    = float(row[2] or 0)
            sap_value    = float(row[3] or 0)
            barges       = row[4] if row[4] else []

            details.append({
                'label': label,
                'total_actual': round(total_actual, 2),
                'lim_actual': round(lim_value, 2),
                'sap_actual': round(sap_value, 2),
                'barges': barges
            })

        return JsonResponse({
            'summary': {
                'x_data': [d['label'] for d in details],
                'y_data_actual': [d['total_actual'] for d in details],
                'y_data_lim': [d['lim_actual'] for d in details],
                'y_data_sap': [d['sap_actual'] for d in details],
            },
            'details': details
        })

    except DatabaseError:
        logger.exception("DB Error in chart selling")
        return JsonResponse({'error': 'Database error'}, status=500)
    except Exception as e:
        logger.exception("Unexpected error in chart selling")
        return JsonResponse({'error': str(e)}, status=500)
    
# Barging Overview
def summary_barging_overview(request):
    try:
        iup_filter  = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year        = request.GET.get("year")
        month       = request.GET.get("month")
        week        = request.GET.get("week")
        date_start  = request.GET.get("date_start")
        date_end    = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        # Resolve Date Range
        if filter_type == "daily" and filter_date:
            ds = de = filter_date

        elif filter_type == "range" and date_start and date_end:
            ds, de = date_start, date_end

        elif filter_type == "monthly" and year and month:
            year = int(year)
            month = int(month)
            last_day = calendar.monthrange(year, month)[1]
            ds = f"{year}-{month:02d}-01"
            de = f"{year}-{month:02d}-{last_day:02d}"

        elif filter_type == "yearly" and year:
            year = int(year)
            ds = f"{year}-01-01"
            de = f"{year}-12-31"

        elif filter_type == "weekly" and week:
            if "-" in str(week):
                y_str, w_str = str(week).split("-")
                start = datetime.strptime(f"{int(y_str)}-W{int(w_str):02d}-1", "%G-W%V-%u")
                end = start + timedelta(days=6)
            else:
                year = int(year)
                month = int(month)
                week = int(week)

                first_day = datetime(year, month, 1)
                start = first_day + timedelta(days=(week - 1) * 7)
                end = start + timedelta(days=6)

                if end.month != month:
                    end = datetime(year, month, calendar.monthrange(year, month)[1])

            ds = start.strftime("%Y-%m-%d")
            de = end.strftime("%Y-%m-%d")

        elif filter_type == "all":
            ds = "2000-01-01"
            de = "2100-12-31"

        else:
            return JsonResponse({"error": "Invalid filter"}, status=400)

        # IUP Filter
        iup_clause_s, iup_params_s = build_iup_clause(iup_filter, "s")

        query = f"""
            WITH barge_group AS (
                SELECT
                    mb.barge_code,
                    MIN(s.date_hauling::date + s.time_hauling) AS start_loading,
                    MAX(s.date_hauling::date + s.time_hauling) AS end_loading,
                    SUM(s.tonnage) AS total_tonnage,
                    SUM(CASE WHEN m.name = 'LIM' THEN s.tonnage ELSE 0 END) AS total_lim,
                    SUM(CASE WHEN m.name = 'SAP' THEN s.tonnage ELSE 0 END) AS total_sap
                FROM selling_barging s
                LEFT JOIN master_barge mb ON mb.id = s.barge_code
                LEFT JOIN master_materials m ON m.id = s.id_material
                WHERE s.date_hauling BETWEEN %s AND %s
                {iup_clause_s}
                GROUP BY mb.barge_code
            )
            SELECT
                COALESCE(COUNT(DISTINCT barge_code), 0) AS total_barge,
                COALESCE(SUM(total_tonnage), 0) AS total_ore,
                COALESCE(SUM(total_lim), 0) AS total_lim,
                COALESCE(SUM(total_sap), 0) AS total_sap,

                COALESCE(
                    ROUND(
                        (SUM(total_tonnage) / NULLIF(COUNT(DISTINCT barge_code), 0))::numeric,
                        2
                    ),
                    0
                ) AS avg_mt,

                COALESCE(
                    ROUND(
                        AVG(EXTRACT(EPOCH FROM (end_loading - start_loading)) / 3600)::numeric,
                        2
                    ),
                    0
                ) AS avg_loading_time,

                COALESCE(
                    json_agg(
                        json_build_object(
                            'barge_code', barge_code,
                            'tonnage', ROUND(total_tonnage::numeric, 2),
                            'lim', ROUND(total_lim::numeric, 2),
                            'sap', ROUND(total_sap::numeric, 2),
                            'loading_time',
                                ROUND(
                                    (EXTRACT(EPOCH FROM (end_loading - start_loading)) / 3600)::numeric,
                                    2
                                ),
                            'start_loading', start_loading,
                            'end_loading', end_loading
                        )
                        ORDER BY total_tonnage DESC
                    ) FILTER (WHERE barge_code IS NOT NULL),
                    '[]'::json
                ) AS barges
            FROM barge_group;
        """

        params = [ds, de] + iup_params_s

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        return JsonResponse({
            "total_barge": int(row[0] or 0),
            "total_ore": float(row[1] or 0),
            "total_lim": float(row[2] or 0),
            "total_sap": float(row[3] or 0),
            "avg_mt": float(row[4] or 0),
            "avg_loading_time": float(row[5] or 0),
            "barges": row[6] or [],
            "meta": {
                "date_start": ds,
                "date_end": de,
                "filter_type": filter_type,
            }
        })

    except DatabaseError:
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)