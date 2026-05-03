from datetime import date, timedelta
import calendar
from django.http import JsonResponse
from django.db import connection

from analytics.services.iup_filter import build_iup_clause

def parse_iso_week(week_value):
    iso_year_str, iso_week_str = str(week_value).split("-")
    return int(iso_year_str), int(iso_week_str)


def build_actual_filter_clause(
    filter_type=None,
    year=None,
    month=None,
    week=None,
    date_val=None,
    date_start=None,
    date_end=None,
    iup_filter=None,
    alias="mp",
):
    today = date.today()

    where_clause = "1=1"
    params = []

    iup_clause, iup_params = build_iup_clause(iup_filter, alias)
    where_clause += iup_clause
    params += iup_params

    date_col = f"{alias}.date_production"

    if filter_type == "daily" and date_val:
        where_clause += f" AND DATE({date_col}) = %s"
        params.append(date_val)

    elif filter_type == "weekly" and week:
        where_clause += f" AND TO_CHAR({date_col}, 'IYYY-IW') = %s"
        params.append(week)

    elif filter_type == "wtd" and week:
        iso_year, iso_week = parse_iso_week(week)

        start_of_week = date.fromisocalendar(iso_year, iso_week, 1)
        end_of_week = start_of_week + timedelta(days=6)
        end_of_wtd = min(today, end_of_week)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_week, end_of_wtd]

    elif filter_type == "monthly" and year and month:
        where_clause += f"""
            AND EXTRACT(YEAR FROM {date_col}) = %s
            AND EXTRACT(MONTH FROM {date_col}) = %s
        """
        params += [year, month]

    elif filter_type == "mtd" and year and month:
        start_of_month = date(int(year), int(month), 1)
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_of_month = date(int(year), int(month), last_day)
        end_of_mtd = min(today, end_of_month)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_month, end_of_mtd]

    elif filter_type == "yearly" and year:
        where_clause += f" AND EXTRACT(YEAR FROM {date_col}) = %s"
        params.append(year)

    elif filter_type == "ytd" and year:
        start_of_year = date(int(year), 1, 1)
        end_of_year = date(int(year), 12, 31)
        end_of_ytd = min(today, end_of_year)

        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [start_of_year, end_of_ytd]

    elif filter_type == "range" and date_start and date_end:
        where_clause += f" AND {date_col} BETWEEN %s AND %s"
        params += [date_start, date_end]

    return where_clause, params


def get_summary_materials_grouped(request):
    return summary_materials_grouped(
        filter_type=request.GET.get("filter_type"),
        year=request.GET.get("year"),
        month=request.GET.get("month"),
        week=request.GET.get("week"),
        date_val=request.GET.get("filter_date") or request.GET.get("date"),
        date_start=request.GET.get("date_start"),
        date_end=request.GET.get("date_end"),
        iup_filter=request.GET.get("iup_id"),
    )


def summary_materials_grouped(
    filter_type=None,
    year=None,
    month=None,
    week=None,
    date_val=None,
    date_start=None,
    date_end=None,
    iup_filter=None,
):
    where_clause, params = build_actual_filter_clause(
        filter_type=filter_type,
        year=year,
        month=month,
        week=week,
        date_val=date_val,
        date_start=date_start,
        date_end=date_end,
        iup_filter=iup_filter,
        alias="mp",
    )

    query = f"""
        SELECT 
            mp.nama_material,
            SUM(COALESCE(mp.ritase, 0)) AS total_ritase,
            SUM(COALESCE(mp.tonnage, 0)) AS total_tonnage
        FROM view_mining_productions mp
        WHERE {where_clause}
        GROUP BY mp.nama_material
        ORDER BY mp.nama_material;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    summary = []
    grand_total_ritase = 0
    grand_total_tonnage = 0

    for material, ritase, tonnage in rows:
        material = material or "Unknown"
        ritase = int(ritase or 0)
        tonnage = float(tonnage or 0)

        grand_total_ritase += ritase
        grand_total_tonnage += tonnage

        summary.append({
            "material": material,
            "ritase": ritase,
            "tonnage": round(tonnage, 2),
            "percentage": 0,
        })

    if grand_total_tonnage > 0:
        for item in summary:
            item["percentage"] = round(
                item["tonnage"] / grand_total_tonnage * 100,
                2,
            )

    return JsonResponse({
        "filter": {
            "filter_type": filter_type,
            "year": year,
            "month": month,
            "week": week,
            "date": date_val,
            "date_start": date_start,
            "date_end": date_end,
            "iup_id": iup_filter,
        },
        "summary": summary,
        "grand_total_ritase": grand_total_ritase,
        "grand_total_tonnage": round(grand_total_tonnage, 2),
    })