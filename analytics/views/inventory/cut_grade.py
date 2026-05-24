# analytics/views/inventory/cut_grade.py
import calendar
from datetime import datetime, timedelta
from django.db import connection

def resolve_cut_date(params):
    filter_type = params.get("filter_type")

    if filter_type == "daily":
        return params.get("filter_date")

    if filter_type == "range":
        return params.get("date_end")

    if filter_type == "monthly":
        year = int(params.get("year"))
        month = int(params.get("month"))
        last_day = calendar.monthrange(year, month)[1]
        return f"{year}-{month:02d}-{last_day:02d}"

    if filter_type == "yearly":
        return f"{int(params.get('year'))}-12-31"

    if filter_type == "weekly":
        week = params.get("week")

        if "-" in str(week):
            y, w = str(week).split("-")
            start = datetime.strptime(
                f"{int(y)}-W{int(w):02d}-1",
                "%G-W%V-%u"
            ).date()
            end = start + timedelta(days=6)
            return end.isoformat()

    return None


def get_inventory_grade_cutoff(params):
    cut_date = resolve_cut_date(params)

    return get_inventory_grade_by_cutoff(
        cut_date=cut_date,
        iup_id=params.get("iup_id")
    )


def get_inventory_grade_by_cutoff(cut_date, iup_id=None):

    where_iup = ""
    query_params = [cut_date]

    if iup_id:
        where_iup = "AND iup_id = %s"
        query_params.append(iup_id)

    query = f"""
        SELECT
            nama_material,
            stockpile,
            SUM(tonnage)::numeric AS total_stock,

            COALESCE(ROUND((
                SUM(tonnage * roa_ni) /
                NULLIF(SUM(CASE
                    WHEN sample_number <> 'Unprepared'
                     AND roa_ni IS NOT NULL
                    THEN tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS ni,

            COALESCE(ROUND((
                SUM(tonnage * roa_fe) /
                NULLIF(SUM(CASE
                    WHEN sample_number <> 'Unprepared'
                     AND roa_ni IS NOT NULL
                    THEN tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS fe,

            COALESCE(ROUND((
                SUM(tonnage * roa_mgo) /
                NULLIF(SUM(CASE
                    WHEN sample_number <> 'Unprepared'
                     AND roa_ni IS NOT NULL
                    THEN tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS mgo,

            COALESCE(ROUND((
                SUM(tonnage * roa_sio2) /
                NULLIF(SUM(CASE
                    WHEN sample_number <> 'Unprepared'
                     AND roa_ni IS NOT NULL
                    THEN tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS sio2,

            COALESCE(ROUND((
                SUM(tonnage * roa_sm) /
                NULLIF(SUM(CASE
                    WHEN sample_number <> 'Unprepared'
                     AND roa_ni IS NOT NULL
                    THEN tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS sm

        FROM view_geology_ore_details_roa
        WHERE tgl_production <= %s
          AND status_dome <> 'Finished'
          {where_iup}
        GROUP BY nama_material, stockpile
        ORDER BY total_stock DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(query, query_params)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    for row in rows:
        row["total_stock"] = round(float(row["total_stock"] or 0), 1)
        row["ni"] = round(float(row["ni"] or 0), 2)
        row["fe"] = round(float(row["fe"] or 0), 2)
        row["mgo"] = round(float(row["mgo"] or 0), 2)
        row["sio2"] = round(float(row["sio2"] or 0), 2)
        row["sm"] = round(float(row["sm"] or 0), 2)

    return {
        "cut_date": cut_date,
        "data": rows,
    }