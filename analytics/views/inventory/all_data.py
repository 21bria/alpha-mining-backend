# views.py
import logging
from django.http import JsonResponse
from django.db import connection, DatabaseError
import pandas as pd
import calendar
from datetime import datetime, timedelta
import itertools
from django.db.models import Sum
from django.utils.timezone import now
from django.db.models.functions import TruncWeek
logger = logging.getLogger(__name__)
import json
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from analytics.services.iup_filter import build_iup_clause


def f2(v):
    return Decimal(v).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)


class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def to_float1(v):
    return round(float(v or 0), 1)

def get_inventory_summary(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")

        iup_clause_op, iup_params_op = build_iup_clause(iup_filter, "op")
        iup_clause_s, iup_params_s = build_iup_clause(iup_filter, "s")

        if filter_type == "range" and date_start and date_end:
            start_ref = date_start
            end_ref = date_end

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
                        return JsonResponse({"error": "Bulan tidak valid (1-12)"}, status=400)
                    if not (1 <= week <= 5):
                        return JsonResponse({"error": "Minggu tidak valid (1-5)"}, status=400)

                    first_day = datetime(year, month, 1)
                    start_date = first_day + timedelta(days=(week - 1) * 7)
                    end_date = start_date + timedelta(days=6)

                    if end_date.month != month:
                        next_month = datetime(year, month, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

                start_ref = start_date.strftime("%Y-%m-%d")
                end_ref = end_date.strftime("%Y-%m-%d")

            except Exception as e:
                return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)

        elif filter_type == "monthly" and year and month:
            year = int(year)
            month = int(month)
            last_day = calendar.monthrange(year, month)[1]

            start_ref = datetime(year, month, 1).date().strftime("%Y-%m-%d")
            end_ref = datetime(year, month, last_day).date().strftime("%Y-%m-%d")

        elif filter_type == "yearly" and year:
            year = int(year)
            start_ref = f"{year}-01-01"
            end_ref = f"{year}-12-31"

        elif filter_type == "all":
            start_ref = "1900-01-01"
            end_ref = "2999-12-31"

        else:
            return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

        query = f"""
            WITH saldo_awal AS (
                SELECT
                    COALESCE((
                        SELECT SUM(
                            CASE
                                WHEN op.status_dome = 'Finished' AND m.name = 'LIM' THEN 0
                                WHEN m.name = 'LIM' THEN op.tonnage
                                ELSE 0
                            END
                        )
                        FROM geology_ore_productions op
                        LEFT JOIN master_materials m ON m.id = op.id_material
                        WHERE op.tgl_production < %s
                        {iup_clause_op}
                    ), 0)
                    -
                    COALESCE((
                        SELECT SUM(
                            CASE
                                WHEN s.sale_dome = 'Finished' AND m.name = 'LIM' THEN 0
                                WHEN m.name = 'LIM' THEN s.tonnage
                                ELSE 0
                            END
                        )
                        FROM selling_barging s
                        LEFT JOIN master_materials m ON m.id = s.id_material
                        WHERE s.date_barge_out < %s
                        AND s.status_barging = 'Complete'
                        {iup_clause_s}
                    ), 0) AS lim_awal,

                    COALESCE((
                        SELECT SUM(
                            CASE
                                WHEN op.status_dome = 'Finished' AND m.name = 'SAP' THEN 0
                                WHEN m.name = 'SAP' THEN op.tonnage
                                ELSE 0
                            END
                        )
                        FROM geology_ore_productions op
                        LEFT JOIN master_materials m ON m.id = op.id_material
                        WHERE op.tgl_production < %s
                        {iup_clause_op}
                    ), 0)
                    -
                    COALESCE((
                        SELECT SUM(
                            CASE
                                WHEN s.sale_dome = 'Finished' AND m.name = 'SAP' THEN 0
                                WHEN m.name = 'SAP' THEN s.tonnage
                                ELSE 0
                            END
                        )
                        FROM selling_barging s
                        LEFT JOIN master_materials m ON m.id = s.id_material
                        WHERE s.date_barge_out < %s
                        AND s.status_barging = 'Complete'
                        {iup_clause_s}
                    ), 0) AS sap_awal
            ),

            incoming AS (
                SELECT
                    COALESCE(SUM(
                        CASE
                            WHEN m.name = 'LIM' AND op.status_dome <> 'Finished' THEN op.tonnage
                            ELSE 0
                        END
                    ), 0) AS lim_in,
                    COALESCE(SUM(
                        CASE
                            WHEN m.name = 'SAP' AND op.status_dome <> 'Finished' THEN op.tonnage
                            ELSE 0
                        END
                    ), 0) AS sap_in
                FROM geology_ore_productions op
                LEFT JOIN master_materials m ON m.id = op.id_material
                WHERE op.tgl_production BETWEEN %s AND %s
                {iup_clause_op}
            ),

            outgoing AS (
                SELECT
                    COALESCE(SUM(
                        CASE
                            WHEN m.name = 'LIM' AND s.sale_dome <> 'Finished' THEN s.tonnage
                            ELSE 0
                        END
                    ), 0) AS lim_out,
                    COALESCE(SUM(
                        CASE
                            WHEN m.name = 'SAP' AND s.sale_dome <> 'Finished' THEN s.tonnage
                            ELSE 0
                        END
                    ), 0) AS sap_out
                FROM selling_barging s
                LEFT JOIN master_materials m ON m.id = s.id_material
                WHERE s.date_barge_out BETWEEN %s AND %s
                AND s.status_barging = 'Complete'
                {iup_clause_s}
            )

            SELECT
                COALESCE(i.lim_in, 0) AS lim_in,
                COALESCE(o.lim_out, 0) AS lim_out,
                sa.lim_awal + (COALESCE(i.lim_in, 0) - COALESCE(o.lim_out, 0)) AS lim_stock,

                COALESCE(i.sap_in, 0) AS sap_in,
                COALESCE(o.sap_out, 0) AS sap_out,
                sa.sap_awal + (COALESCE(i.sap_in, 0) - COALESCE(o.sap_out, 0)) AS sap_stock,

                COALESCE(i.lim_in, 0) + COALESCE(i.sap_in, 0) AS total_in,
                COALESCE(o.lim_out, 0) + COALESCE(o.sap_out, 0) AS total_out,
                (sa.lim_awal + sa.sap_awal) +
                ((COALESCE(i.lim_in, 0) + COALESCE(i.sap_in, 0)) -
                 (COALESCE(o.lim_out, 0) + COALESCE(o.sap_out, 0))) AS total_stock
            FROM incoming i, outgoing o, saldo_awal sa
        """

        params = (
            [start_ref] + iup_params_op +
            [start_ref] + iup_params_s +
            [start_ref] + iup_params_op +
            [start_ref] + iup_params_s +
            [start_ref, end_ref] + iup_params_op +
            [start_ref, end_ref] + iup_params_s
        )

        print("START_REF:", start_ref)
        print("END_REF:", end_ref)
        print("PARAMS:", params)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        return JsonResponse({
            "lim_in": to_float1(row[0]),
            "lim_out": to_float1(row[1]),
            "lim_stock": to_float1(row[2]),
            "sap_in": to_float1(row[3]),
            "sap_out": to_float1(row[4]),
            "sap_stock": to_float1(row[5]),
            "total_in": to_float1(row[6]),
            "total_out": to_float1(row[7]),
            "total_stock": to_float1(row[8]),
        })

    except DatabaseError as e:
        logger.exception("Database query failed.")
        return JsonResponse({"error": str(e)}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in get_inventory_summary")
        return JsonResponse({"error": str(e)}, status=500)

# Create Chart Ore
def get_chart_inventory(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")

        x_labels = []
        data_stock = []
        data_out = []
        balance = []

        iup_clause_op, iup_params_op = build_iup_clause(iup_filter, "op")
        iup_clause_s, iup_params_s = build_iup_clause(iup_filter, "s")
        iup_clause_osb, iup_params_osb = build_iup_clause(iup_filter, "osb")

        if filter_type == "range" and date_start and date_end:
            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                incoming AS (
                    SELECT
                        op.tgl_production::date AS date,
                        SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END) AS in_stock,
                        SUM(op.tonnage) AS total_in
                    FROM geology_ore_productions op
                    WHERE op.tgl_production BETWEEN %s AND %s
                    {iup_clause_op}
                    GROUP BY op.tgl_production
                ),
                barging AS (
                    SELECT
                        s.date_hauling::date AS date,
                        SUM(CASE WHEN s.sale_dome = 'Finished' THEN 0 ELSE s.tonnage END) AS out_stock,
                        SUM(s.tonnage) AS total_barging
                    FROM selling_barging s
                    WHERE s.date_hauling BETWEEN %s AND %s
                    AND s.status_barging = 'Complete'
                    {iup_clause_s}
                    GROUP BY s.date_hauling
                ),
                outgoing AS (
                    SELECT
                        s.date_hauling::date AS date,
                        SUM(CASE WHEN s.sale_dome = 'Finished' THEN 0 ELSE s.tonnage END) AS out_stock,
                        SUM(s.tonnage) AS total_out
                    FROM selling_barging s
                    WHERE s.date_hauling BETWEEN %s AND %s
                    AND s.status_barging = 'Complete'
                    {iup_clause_s}
                    GROUP BY s.date_hauling
                ),
                saldo_awal AS (
                    SELECT
                        COALESCE((
                            SELECT SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END)
                            FROM geology_ore_productions op
                            WHERE op.tgl_production < %s
                            {iup_clause_op}
                        ), 0)
                        -
                        COALESCE((
                            SELECT SUM(CASE WHEN osb.sale_dome = 'Finished' THEN 0 ELSE osb.tonnage END)
                            FROM selling_barging osb
                            WHERE osb.date_hauling < %s
                            AND osb.status_barging = 'Complete'
                            {iup_clause_osb}
                        ), 0) AS value
                )
                SELECT
                    TO_CHAR(t.date, 'DD') AS label,
                    COALESCE(i.total_in, 0) AS total_in,
                    COALESCE(b.total_barging, 0) AS total_barging,
                    COALESCE(o.total_out, 0) AS total_out,
                    SUM(COALESCE(i.in_stock, 0) - COALESCE(o.out_stock, 0))
                        OVER (ORDER BY t.date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                        + (SELECT value FROM saldo_awal) AS running_balance
                FROM tanggal t
                LEFT JOIN incoming i ON t.date = i.date
                LEFT JOIN barging b ON t.date = b.date
                LEFT JOIN outgoing o ON t.date = o.date
                ORDER BY t.date;
            """

            params = (
                [date_start, date_end] +
                [date_start, date_end] + iup_params_op +
                [date_start, date_end] + iup_params_s +
                [date_start, date_end] + iup_params_s +
                [date_start] + iup_params_op +
                [date_start] + iup_params_osb
            )

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

            start_ref = start_date.strftime("%Y-%m-%d")
            end_ref = end_date.strftime("%Y-%m-%d")

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                incoming AS (
                    SELECT
                        op.tgl_production::date AS date,
                        SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END) AS in_stock,
                        SUM(op.tonnage) AS total_in
                    FROM geology_ore_productions op
                    WHERE op.tgl_production BETWEEN %s AND %s
                    {iup_clause_op}
                    GROUP BY op.tgl_production::date
                ),
                barging AS (
                    SELECT
                        osb.date_hauling::date AS date,
                        SUM(CASE WHEN osb.sale_dome = 'Finished' THEN 0 ELSE osb.tonnage END) AS out_barging,
                        SUM(osb.tonnage) AS total_barging
                    FROM selling_barging osb
                    WHERE osb.date_hauling BETWEEN %s AND %s
                    AND osb.status_barging = 'Complete'
                    {iup_clause_osb}
                    GROUP BY osb.date_hauling::date
                ),
                outgoing AS (
                    SELECT
                        osb.date_barge_out::date AS date,
                        SUM(CASE WHEN osb.sale_dome = 'Finished' THEN 0 ELSE osb.tonnage END) AS out_stock,
                        SUM(osb.tonnage) AS total_out
                    FROM selling_barging osb
                    WHERE osb.date_barge_out BETWEEN %s AND %s
                    AND osb.status_barging = 'Complete'
                    {iup_clause_osb}
                    GROUP BY osb.date_barge_out::date
                ),
                daily AS (
                    SELECT
                        t.date,
                        COALESCE(i.total_in, 0) AS total_in,
                        COALESCE(b.total_barging, 0) AS total_barging,
                        COALESCE(o.total_out, 0) AS total_out,
                        COALESCE(i.in_stock, 0) AS in_stock,
                        COALESCE(o.out_stock, 0) AS out_stock
                    FROM tanggal t
                    LEFT JOIN incoming i ON t.date = i.date
                    LEFT JOIN barging b ON t.date = b.date
                    LEFT JOIN outgoing o ON t.date = o.date
                ),
                saldo_awal AS (
                    SELECT
                        COALESCE((
                            SELECT SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END)
                            FROM geology_ore_productions op
                            WHERE op.tgl_production < %s
                            {iup_clause_op}
                        ), 0)
                        -
                        COALESCE((
                            SELECT SUM(CASE WHEN osb.sale_dome = 'Finished' THEN 0 ELSE osb.tonnage END)
                            FROM selling_barging osb
                            WHERE osb.date_barge_out < %s
                            AND osb.status_barging = 'Complete'
                            {iup_clause_osb}
                        ), 0) AS value
                )
                SELECT
                    TRIM(TO_CHAR(date, 'Day')) AS label,
                    total_in,
                    total_barging,
                    total_out,
                    SUM(in_stock - out_stock) OVER (
                        ORDER BY date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) + (SELECT value FROM saldo_awal) AS running_balance
                FROM daily
                GROUP BY label, total_in, total_barging, total_out, in_stock, out_stock, date
                ORDER BY ARRAY_POSITION(
                    ARRAY['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
                    TRIM(TO_CHAR(date, 'Day'))
                );
            """

            params = (
                [start_ref, end_ref] +
                [start_ref, end_ref] + iup_params_op +
                [start_ref, end_ref] + iup_params_osb +
                [start_ref, end_ref] + iup_params_osb +
                [start_ref] + iup_params_op +
                [start_ref] + iup_params_osb
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
                incoming AS (
                    SELECT
                        op.tgl_production::date AS date,
                        SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END) AS in_stock,
                        SUM(op.tonnage) AS total_in
                    FROM geology_ore_productions op
                    WHERE op.tgl_production BETWEEN %s AND %s
                    {iup_clause_op}
                    GROUP BY op.tgl_production
                ),
                barging AS (
                    SELECT
                        s.date_hauling::date AS date,
                        SUM(CASE WHEN s.sale_dome = 'Finished' THEN 0 ELSE s.tonnage END) AS out_stock,
                        SUM(s.tonnage) AS total_out
                    FROM selling_barging s
                    WHERE s.date_hauling BETWEEN %s AND %s
                    AND s.status_barging='Complete'
                    {iup_clause_s}
                    GROUP BY s.date_hauling
                ),
                outgoing AS (
                    SELECT
                        s.date_barge_out::date AS date,
                        SUM(CASE WHEN s.sale_dome = 'Finished' THEN 0 ELSE s.tonnage END) AS out_stock,
                        SUM(s.tonnage) AS total_out
                    FROM selling_barging s
                    WHERE s.date_barge_out BETWEEN %s AND %s
                    AND s.status_barging = 'Complete'
                    {iup_clause_s}
                    GROUP BY s.date_barge_out
                ),
                saldo_awal AS (
                    SELECT
                        COALESCE((
                            SELECT SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END)
                            FROM geology_ore_productions op
                            WHERE op.tgl_production < %s
                            {iup_clause_op}
                        ), 0)
                        -
                        COALESCE((
                            SELECT SUM(CASE WHEN osb.sale_dome = 'Finished' THEN 0 ELSE osb.tonnage END)
                            FROM selling_barging osb
                            WHERE osb.date_barge_out < %s
                            AND osb.status_barging = 'Complete'
                            {iup_clause_osb}
                        ), 0) AS value
                )
                SELECT
                    TO_CHAR(t.date, 'DD') AS label,
                    COALESCE(i.total_in, 0) AS total_in,
                    COALESCE(b.total_out, 0) AS total_barging,
                    COALESCE(o.total_out, 0) AS total_out,
                    SUM(COALESCE(i.in_stock, 0) - COALESCE(o.out_stock, 0))
                        OVER (ORDER BY t.date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                        + (SELECT value FROM saldo_awal) AS running_balance
                FROM tanggal t
                LEFT JOIN incoming i ON t.date = i.date
                LEFT JOIN barging b ON t.date = b.date
                LEFT JOIN outgoing o ON t.date = o.date
                ORDER BY t.date;
            """

            params = (
                [tgl_pertama, tgl_terakhir] +
                [tgl_pertama, tgl_terakhir] + iup_params_op +
                [tgl_pertama, tgl_terakhir] + iup_params_s +
                [tgl_pertama, tgl_terakhir] + iup_params_s +
                [tgl_pertama] + iup_params_op +
                [tgl_pertama] + iup_params_osb
            )

        elif filter_type == "yearly" and year:
            year = int(year)

            query = f"""
                WITH bulan AS (
                    SELECT generate_series(1, 12) AS month
                ),
                incoming AS (
                    SELECT
                        EXTRACT(MONTH FROM op.tgl_production)::int AS month,
                        SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END) AS in_stock,
                        SUM(op.tonnage) AS total_in
                    FROM geology_ore_productions op
                    WHERE EXTRACT(YEAR FROM op.tgl_production) = %s
                    {iup_clause_op}
                    GROUP BY EXTRACT(MONTH FROM op.tgl_production)
                ),
                barging AS (
                    SELECT
                        EXTRACT(MONTH FROM s.date_hauling)::int AS month,
                        SUM(CASE WHEN s.sale_dome = 'Finished' THEN 0 ELSE s.tonnage END) AS out_stock,
                        SUM(s.tonnage) AS total_out
                    FROM selling_barging s
                    WHERE EXTRACT(YEAR FROM s.date_hauling) = %s
                    AND s.status_barging = 'Complete'
                    {iup_clause_s}
                    GROUP BY EXTRACT(MONTH FROM s.date_hauling)
                ),
                outgoing AS (
                    SELECT
                        EXTRACT(MONTH FROM s.date_barge_out)::int AS month,
                        SUM(CASE WHEN s.sale_dome = 'Finished' THEN 0 ELSE s.tonnage END) AS out_stock,
                        SUM(s.tonnage) AS total_out
                    FROM selling_barging s
                    WHERE EXTRACT(YEAR FROM s.date_barge_out) = %s
                    AND s.status_barging = 'Complete'
                    {iup_clause_s}
                    GROUP BY EXTRACT(MONTH FROM s.date_barge_out)
                ),
                saldo_awal AS (
                    SELECT
                        COALESCE((
                            SELECT SUM(CASE WHEN op.status_dome = 'Finished' THEN 0 ELSE op.tonnage END)
                            FROM geology_ore_productions op
                            WHERE EXTRACT(YEAR FROM op.tgl_production) < %s
                            {iup_clause_op}
                        ), 0)
                        -
                        COALESCE((
                            SELECT SUM(CASE WHEN osb.sale_dome = 'Finished' THEN 0 ELSE osb.tonnage END)
                            FROM selling_barging osb
                            WHERE EXTRACT(YEAR FROM osb.date_barge_out) < %s
                            AND osb.status_barging = 'Complete'
                            {iup_clause_osb}
                        ), 0) AS value
                )
                SELECT
                    TO_CHAR(TO_DATE(bulan.month::text, 'MM'), 'Mon') AS label,
                    COALESCE(i.total_in, 0) AS total_in,
                    COALESCE(b.total_out, 0) AS total_barging,
                    COALESCE(o.total_out, 0) AS total_out,
                    SUM(COALESCE(i.in_stock, 0) - COALESCE(o.out_stock, 0))
                        OVER (ORDER BY bulan.month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                        + (SELECT value FROM saldo_awal) AS running_balance
                FROM bulan
                LEFT JOIN incoming i ON bulan.month = i.month
                LEFT JOIN barging b ON bulan.month = b.month
                LEFT JOIN outgoing o ON bulan.month = o.month
                ORDER BY bulan.month;
            """

            params = (
                [year] + iup_params_op +
                [year] + iup_params_s +
                [year] + iup_params_s +
                [year] + iup_params_op +
                [year] + iup_params_osb
            )

        elif filter_type == "all":
            query = f"""
                WITH incoming AS (
                    SELECT
                        EXTRACT(YEAR FROM op.tgl_production)::int AS year,
                        SUM(op.tonnage) AS total_in
                    FROM geology_ore_productions op
                    WHERE 1=1
                    {iup_clause_op}
                    GROUP BY EXTRACT(YEAR FROM op.tgl_production)
                ),
                outgoing AS (
                    SELECT
                        EXTRACT(YEAR FROM s.date_hauling)::int AS year,
                        SUM(s.tonnage) AS total_out
                    FROM selling_barging s
                    WHERE s.status_barging='Complete'
                    {iup_clause_s}
                    GROUP BY EXTRACT(YEAR FROM s.date_hauling)
                )
                SELECT
                    COALESCE(i.year, o.year) AS label,
                    COALESCE(i.total_in, 0) AS total_in,
                    COALESCE(o.total_out, 0) AS total_out,
                    SUM(COALESCE(i.total_in, 0) - COALESCE(o.total_out, 0))
                        OVER (ORDER BY COALESCE(i.year, o.year)) AS running_balance
                FROM incoming i
                FULL OUTER JOIN outgoing o ON i.year = o.year
                ORDER BY label
            """
            params = iup_params_op + iup_params_s

        else:
            return JsonResponse({"error": "Invalid or incomplete filter parameters"}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        for row in results:
            x_labels.append(str(row[0]))
            data_stock.append(round(float(row[1] or 0), 0))
            data_out.append(round(float(row[2] or 0), 0))
            balance.append(round(float(row[4] or 0), 0))

        return JsonResponse({
            "x_data": x_labels,
            "y_data_stock": data_stock,
            "y_data_out": data_out,
            "y_data_balance": balance,
        })

    except DatabaseError:
        logger.exception("DB Error in get_chart_inventory")
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in get_chart_inventory")
        return JsonResponse({"error": str(e)}, status=500)
    
# Ach. Ore Production
def get_grade_class(ni, mgo, fe):
    if ni is None or mgo is None or fe is None:
        return "NULL"
    if ni >= 1.6 and mgo >= 9.0 and fe <= 27.0:
        return "HGS"
    elif 1.2 <= ni < 1.6 and mgo >= 9.0 and fe <= 27.0:
        return "MGS"
    elif ni < 1.2 and 9.0 <= mgo <= 20.0 and fe <= 27.0:
        return "LGS"
    elif ni >= 1.1 and mgo < 9.0 and fe >= 27.0:
        return "HGL"
    elif ni < 1.1 and mgo < 9.0 and fe >= 27.0:
        return "LGL"
    elif ni < 0.9 and mgo < 9.0 and fe < 27.0:
        return "OB"
    elif ni < 1.2 and mgo > 20.0 and fe >= 27.0:
        return "WASTE"
    else:
        return "???"

def get_grade_roa(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        filter_date = request.GET.get("filter_date")

        where_clause = "WHERE 1=1"
        params = []

        # filter iup
        if iup_filter:
            iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
            if iup_ids:
                placeholders = ",".join(["%s"] * len(iup_ids))
                where_clause += f" AND iup_id IN ({placeholders})"
                params += iup_ids

        # filter periode
        if filter_type == "daily" and filter_date:
            where_clause += " AND tgl_production = %s"
            params += [filter_date]

        elif filter_type == "range" and date_start and date_end:
            where_clause += " AND tgl_production BETWEEN %s AND %s"
            params += [date_start, date_end]

        elif filter_type == "weekly" and week:
            where_clause += " AND TO_CHAR(tgl_production, 'IYYY-IW') = %s"
            params += [week]

        elif filter_type == "monthly" and year and month:
            where_clause += """
                AND EXTRACT(YEAR FROM tgl_production) = %s
                AND EXTRACT(MONTH FROM tgl_production) = %s
            """
            params += [year, month]

        elif filter_type == "yearly" and year:
            where_clause += " AND EXTRACT(YEAR FROM tgl_production) = %s"
            params += [year]

        elif filter_type == "all":
            pass

        else:
            return JsonResponse({"error": "Invalid filter type"}, status=400)

        sql_query = f"""
            SELECT
                nama_material,
                SUM(tonnage) AS total_ore,
                SUM(
                    CASE
                        WHEN ROA_Ni IS NOT NULL AND sample_number <> 'Unprepared'
                        THEN tonnage ELSE 0
                    END
                ) AS released,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_Ni) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS ni,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_Co) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS co,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_Al2O3) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS al2o3,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_CaO) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS cao,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_Cr2O3) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS cr2o3,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_Fe2O3) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS fe2o3,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_Fe) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS fe,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_MgO) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS mgo,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_MC) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS mc,
                COALESCE(ROUND((
                    SUM(tonnage * ROA_SiO2) /
                    NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                )::numeric, 2), 0) AS sio2,
                ROUND(COALESCE((
                    (
                        SUM(tonnage * ROA_SiO2) /
                        NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0)
                    ) /
                    (
                        NULLIF(
                            SUM(tonnage * ROA_MgO) /
                            NULLIF(SUM(CASE WHEN sample_number <> 'Unprepared' AND ROA_Ni IS NOT NULL THEN tonnage ELSE 0 END), 0),
                            0
                        ) + 0.000001
                    )
                ), 0)::numeric, 2) AS sm
            FROM view_geology_ore_details_roa
            {where_clause}
            GROUP BY nama_material
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_query, params)
            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for row in result:
            row["total_ore"] = round(float(row["total_ore"] or 0), 1)
            row["released"] = round(float(row["released"] or 0), 1)
            row["ni"] = round(float(row["ni"] or 0), 2)
            row["co"] = round(float(row["co"] or 0), 2)
            row["al2o3"] = round(float(row["al2o3"] or 0), 2)
            row["cao"] = round(float(row["cao"] or 0), 2)
            row["cr2o3"] = round(float(row["cr2o3"] or 0), 2)
            row["fe"] = round(float(row["fe"] or 0), 2)
            row["mgo"] = round(float(row["mgo"] or 0), 2)
            row["sio2"] = round(float(row["sio2"] or 0), 2)
            row["mc"] = round(float(row["mc"] or 0), 2)
            row["sm"] = round(float(row["sm"] or 0), 2)
            row["grade"] = get_grade_class(row["ni"], row["mgo"], row["fe"])

        return JsonResponse({
            "data": result,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)