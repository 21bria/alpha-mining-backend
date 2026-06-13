import calendar
import logging
from datetime import date

from django.http import JsonResponse
from django.db import connection, DatabaseError

from analytics.services.iup_filter import build_iup_clause

logger = logging.getLogger(__name__)


def to_float1(v):
    return round(float(v or 0), 1)


def safe_ach(actual, plan):
    return round((float(actual or 0) / float(plan or 0) * 100), 1) if float(plan or 0) > 0 else 0.0


def build_barging_filter_clause(
    filter_type="all",
    year=None,
    month=None,
    week=None,
    filter_date=None,
    period_start=None,
    period_end=None,
    iup_filter=None,
):
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    actual_iup_clause, actual_iup_params = build_iup_clause(iup_filter, "vsd")
    plan_iup_clause, plan_iup_params = build_iup_clause(iup_filter, "pb")

    where_actual += actual_iup_clause
    where_plan += plan_iup_clause

    actual_params += actual_iup_params
    plan_params += plan_iup_params

    today = date.today()

    if filter_type == "daily":
        target_date = filter_date or today.isoformat()

        where_actual += " AND DATE(vsd.date_hauling) = %s"
        where_plan += " AND DATE(pb.date_plan) = %s"

        actual_params.append(target_date)
        plan_params.append(target_date)

    elif filter_type == "weekly":
        if not week:
            raise ValueError("week wajib diisi untuk filter weekly")

        if "-" in str(week):
            iso_year, iso_week = map(int, str(week).split("-"))
        else:
            if not year:
                raise ValueError("year wajib diisi untuk filter weekly")

            iso_year = int(year)
            iso_week = int(week)

        start_date = date.fromisocalendar(iso_year, iso_week, 1)
        end_date = date.fromisocalendar(iso_year, iso_week, 7)

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "wtd":
        if not week:
            raise ValueError("week wajib diisi untuk filter wtd")

        if "-" in str(week):
            iso_year, iso_week = map(int, str(week).split("-"))
        else:
            if not year:
                raise ValueError("year wajib diisi untuk filter wtd")

            iso_year = int(year)
            iso_week = int(week)

        start_date = date.fromisocalendar(iso_year, iso_week, 1)
        week_end = date.fromisocalendar(iso_year, iso_week, 7)
        end_date = min(today, week_end)

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "monthly":
        year = int(year)
        month = int(month)

        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "mtd":
        year = int(year)
        month = int(month)

        start_date = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])
        end_date = min(today, month_end)

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "yearly":
        year = int(year)

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "ytd":
        year = int(year)

        start_date = date(year, 1, 1)
        year_end = date(year, 12, 31)
        end_date = min(today, year_end)

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [start_date, end_date]
        plan_params += [start_date, end_date]

    elif filter_type == "range":
        if not period_start or not period_end:
            raise ValueError("period_start dan period_end wajib diisi untuk filter range")

        where_actual += " AND DATE(vsd.date_hauling) BETWEEN %s AND %s"
        where_plan += " AND DATE(pb.date_plan) BETWEEN %s AND %s"

        actual_params += [period_start, period_end]
        plan_params += [period_start, period_end]

    elif filter_type == "all":
        pass

    else:
        raise ValueError(f"filter_type tidak valid: {filter_type}")

    return where_actual, where_plan, actual_params + plan_params


def get_barging_summary_dataframe(where_actual, where_plan, params):
    query = f"""
        WITH actual AS (
            SELECT
                COALESCE(SUM(CASE WHEN vsd.material = 'LIM' THEN vsd.tonnage ELSE 0 END), 0)::numeric AS lim_actual,
                COALESCE(SUM(CASE WHEN vsd.material = 'SAP' THEN vsd.tonnage ELSE 0 END), 0)::numeric AS sap_actual
            FROM view_selling_details vsd
            WHERE {where_actual}
        ),

        plan AS (
            SELECT
                COALESCE(SUM(pb.lim), 0)::numeric AS lim_plan,
                COALESCE(SUM(pb.sap), 0)::numeric AS sap_plan
            FROM mining_plan_barging pb
            WHERE {where_plan}
              AND COALESCE(pb.is_deleted, false) = false
        )

        SELECT
            ROUND(a.lim_actual, 2) AS lim_actual,
            ROUND(p.lim_plan, 2) AS lim_plan,

            ROUND(a.sap_actual, 2) AS sap_actual,
            ROUND(p.sap_plan, 2) AS sap_plan,

            ROUND((a.lim_actual + a.sap_actual), 2) AS total_actual,
            ROUND((p.lim_plan + p.sap_plan), 2) AS total_plan
        FROM actual a
        CROSS JOIN plan p
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        row = cursor.fetchone()

    return row


def generate_barging_summary(row, label):
    lim_actual = to_float1(row[0])
    lim_plan = to_float1(row[1])

    sap_actual = to_float1(row[2])
    sap_plan = to_float1(row[3])

    total_actual = to_float1(row[4])
    total_plan = to_float1(row[5])

    return {
        "label": label,

        "total_barging": total_actual,
        "total_plan": total_plan,
        "achievement": safe_ach(total_actual, total_plan),

        "total_lim": lim_actual,
        "lim_plan": lim_plan,
        "lim_achievement": safe_ach(lim_actual, lim_plan),

        "total_sap": sap_actual,
        "sap_plan": sap_plan,
        "sap_achievement": safe_ach(sap_actual, sap_plan),
    }


def get_barging_management(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type") or "all"

        filter_year = (
            request.GET.get("yearly")
            or request.GET.get("year")
        )

        filter_month = (
            request.GET.get("monthly")
            or request.GET.get("month")
        )

        filter_week = (
            request.GET.get("weekly")
            or request.GET.get("week")
        )
        filter_date = request.GET.get("filter_date")

        period_start = (
            request.GET.get("period_start")
            or request.GET.get("date_start")
        )
        period_end = (
            request.GET.get("period_end")
            or request.GET.get("date_end")
        )

        result = {}

        if filter_type == "monthly":
            wa, wp, params = build_barging_filter_clause(
                "monthly",
                year=filter_year,
                month=filter_month,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["monthly"] = generate_barging_summary(row, "MONTHLY")

            wa, wp, params = build_barging_filter_clause(
                "mtd",
                year=filter_year,
                month=filter_month,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["mtd"] = generate_barging_summary(row, "MTD")

        elif filter_type == "weekly":
            wa, wp, params = build_barging_filter_clause(
                "weekly",
                year=filter_year,
                week=filter_week,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["weekly"] = generate_barging_summary(row, "WEEKLY")

            wa, wp, params = build_barging_filter_clause(
                "wtd",
                year=filter_year,
                week=filter_week,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["wtd"] = generate_barging_summary(row, "WTD")

        elif filter_type == "yearly":
            wa, wp, params = build_barging_filter_clause(
                "yearly",
                year=filter_year,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["yearly"] = generate_barging_summary(row, "YEARLY")

            wa, wp, params = build_barging_filter_clause(
                "ytd",
                year=filter_year,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["ytd"] = generate_barging_summary(row, "YTD")

        elif filter_type == "range":
            wa, wp, params = build_barging_filter_clause(
                "range",
                period_start=period_start,
                period_end=period_end,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["range"] = generate_barging_summary(row, "RANGE")

        elif filter_type == "daily":
            wa, wp, params = build_barging_filter_clause(
                "daily",
                filter_date=filter_date,
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["daily"] = generate_barging_summary(row, "DAILY")

        else:
            wa, wp, params = build_barging_filter_clause(
                "all",
                iup_filter=iup_filter,
            )
            row = get_barging_summary_dataframe(wa, wp, params)
            result["all"] = generate_barging_summary(row, "ALL")

        return JsonResponse(result, safe=False)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    except DatabaseError:
        logger.exception("Database query failed.")
        return JsonResponse({"error": "Database error"}, status=500)

    except Exception as e:
        logger.exception("Unexpected error in get_barging_management")
        return JsonResponse({"error": str(e)}, status=500)

