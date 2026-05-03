import calendar
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import connection, DatabaseError
from analytics.services.iup_filter import build_iup_clause

def resolve_period(request):
    filter_type = request.GET.get("filter_type")
    year = request.GET.get("year")
    month = request.GET.get("month")
    week = request.GET.get("week")
    date_start = request.GET.get("date_start")
    date_end = request.GET.get("date_end")
    filter_date = request.GET.get("filter_date")

    if filter_type == "daily" and filter_date:
        return filter_date, filter_date

    if filter_type == "range" and date_start and date_end:
        return date_start, date_end

    if filter_type == "monthly" and year and month:
        y = int(year)
        m = int(month)
        last_day = calendar.monthrange(y, m)[1]
        return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last_day:02d}"

    if filter_type == "weekly" and year and month and week:
        if "-" in str(week):
            y_str, w_str = str(week).split("-")
            y = int(y_str)
            w = int(w_str)
            start = datetime.strptime(f"{y}-W{w:02d}-1", "%G-W%V-%u").date()
            end = start + timedelta(days=6)
            return start, end

        y = int(year)
        m = int(month)
        w = int(week)

        first_day = datetime(y, m, 1).date()
        start = first_day + timedelta(days=(w - 1) * 7)
        end = start + timedelta(days=6)

        if end.month != m:
            last_day = calendar.monthrange(y, m)[1]
            end = datetime(y, m, last_day).date()

        return start, end

    if filter_type == "yearly" and year:
        y = int(year)
        return f"{y}-01-01", f"{y}-12-31"

    return None, None

def get_production_grade(request):
    try:
        iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
        filter_type = request.GET.get("filter_type")
        year = request.GET.get("year")
        month = request.GET.get("month")
        week = request.GET.get("week")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        material = request.GET.get("material")

        op_iup_clause, op_iup_params = build_iup_clause(iup_filter, "op")

        material_clause = ""
        material_params = []
        if material:
            material_clause = " AND TRIM(op.nama_material) = %s "
            material_params.append(material)

        grade_sql = """
            SUM(op.tonnage)::numeric AS total_ore,

            SUM(
                CASE
                    WHEN op.roa_ni IS NOT NULL
                     AND op.sample_number <> 'Unprepared'
                    THEN op.tonnage ELSE 0
                END
            )::numeric AS released_ore,

            COALESCE(ROUND((
                SUM(op.tonnage * op.roa_ni) /
                NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS ni,

            COALESCE(ROUND((
                SUM(op.tonnage * op.roa_co) /
                NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS co,

            COALESCE(ROUND((
                SUM(op.tonnage * op.roa_fe) /
                NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS fe,

            COALESCE(ROUND((
                SUM(op.tonnage * op.roa_mgo) /
                NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS mgo,

            COALESCE(ROUND((
                SUM(op.tonnage * op.roa_sio2) /
                NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0)
            )::numeric, 2), 0) AS sio2,

            ROUND(COALESCE((
                (
                    SUM(op.tonnage * op.roa_sio2) /
                    NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0)
                ) /
                (
                    NULLIF(
                        SUM(op.tonnage * op.roa_mgo) /
                        NULLIF(SUM(CASE WHEN op.sample_number <> 'Unprepared' AND op.roa_ni IS NOT NULL THEN op.tonnage ELSE 0 END), 0),
                        0
                    ) + 0.000001
                )
            ), 0)::numeric, 2) AS sm
        """

        if filter_type == "range" and date_start and date_end:
            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
                ),
                incoming AS (
                    SELECT
                        op.tgl_production::date AS date,
                        {grade_sql}
                    FROM view_geology_ore_details_roa op
                    WHERE op.direct = 'No'
                      AND op.tgl_production::date BETWEEN %s::date AND %s::date
                      {material_clause}
                      {op_iup_clause}
                    GROUP BY op.tgl_production::date
                )
                SELECT
                    TO_CHAR(tanggal.date, 'YYYY-MM-DD') AS label,
                    COALESCE(i.total_ore, 0),
                    COALESCE(i.released_ore, 0),
                    COALESCE(i.ni, 0),
                    COALESCE(i.co, 0),
                    COALESCE(i.fe, 0),
                    COALESCE(i.mgo, 0),
                    COALESCE(i.sio2, 0),
                    COALESCE(i.sm, 0)
                FROM tanggal
                LEFT JOIN incoming i ON tanggal.date = i.date
                ORDER BY tanggal.date
            """
            params = [date_start, date_end, date_start, date_end, *material_params, *op_iup_params]

        elif filter_type == "weekly" and year and month and week:
            try:
                if "-" in str(week):
                    year_str, week_str = str(week).split("-")
                    y = int(year_str)
                    w = int(week_str)

                    start_date = datetime.strptime(f"{y}-W{w:02d}-1", "%G-W%V-%u")
                    end_date = start_date + timedelta(days=6)
                else:
                    y = int(year)
                    m = int(month)
                    w = int(week)

                    first_day = datetime(y, m, 1)
                    start_date = first_day + timedelta(days=(w - 1) * 7)
                    end_date = start_date + timedelta(days=6)

                    if end_date.month != m:
                        next_month = datetime(y, m, 28) + timedelta(days=4)
                        end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

            except Exception as e:
                return JsonResponse({"error": f"Invalid week format: {str(e)}"}, status=400)

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day') AS date
                ),
                incoming AS (
                    SELECT
                        op.tgl_production::date AS date,
                        TRIM(TO_CHAR(op.tgl_production, 'Day')) AS day,

                        {grade_sql}

                    FROM view_geology_ore_details_roa op
                    WHERE op.direct = 'No'
                    AND op.tgl_production::date BETWEEN %s::date AND %s::date
                    {material_clause}
                    {op_iup_clause}
                    GROUP BY op.tgl_production::date
                ),
                combine AS (
                    SELECT
                        tanggal.date,
                        TRIM(TO_CHAR(tanggal.date, 'Day')) AS day_name,
                        i.*
                    FROM tanggal
                    LEFT JOIN incoming i ON tanggal.date = i.date
                )
                SELECT
                    day_name AS label,
                    COALESCE(SUM(total_ore), 0),
                    COALESCE(SUM(released_ore), 0),
                    COALESCE(AVG(ni), 0),
                    COALESCE(AVG(co), 0),
                    COALESCE(AVG(fe), 0),
                    COALESCE(AVG(mgo), 0),
                    COALESCE(AVG(sio2), 0),
                    COALESCE(AVG(sm), 0)
                FROM combine
                GROUP BY day_name
                ORDER BY ARRAY_POSITION(
                    ARRAY['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
                    day_name
                )
            """

            params = [
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                *material_params,
                *op_iup_params,
            ]
            
        elif filter_type == "monthly" and year and month:
            y = int(year)
            m = int(month)
            last_day = calendar.monthrange(y, m)[1]
            tgl_pertama = datetime(y, m, 1).date()
            tgl_terakhir = datetime(y, m, last_day).date()

            query = f"""
                WITH tanggal AS (
                    SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS date
                ),
                incoming AS (
                    SELECT
                        op.tgl_production::date AS date,
                        {grade_sql}
                    FROM view_geology_ore_details_roa op
                    WHERE op.direct = 'No'
                      AND op.tgl_production::date BETWEEN %s::date AND %s::date
                      {material_clause}
                      {op_iup_clause}
                    GROUP BY op.tgl_production::date
                )
                SELECT
                    TO_CHAR(tanggal.date, 'DD') AS label,
                    COALESCE(i.total_ore, 0),
                    COALESCE(i.released_ore, 0),
                    COALESCE(i.ni, 0),
                    COALESCE(i.co, 0),
                    COALESCE(i.fe, 0),
                    COALESCE(i.mgo, 0),
                    COALESCE(i.sio2, 0),
                    COALESCE(i.sm, 0)
                FROM tanggal
                LEFT JOIN incoming i ON tanggal.date = i.date
                ORDER BY tanggal.date
            """
            params = [tgl_pertama, tgl_terakhir, tgl_pertama, tgl_terakhir, *material_params, *op_iup_params]

        elif filter_type == "yearly" and year:
            query = f"""
                WITH bulan AS (
                    SELECT generate_series(1, 12) AS month
                ),
                incoming AS (
                    SELECT
                        EXTRACT(MONTH FROM op.tgl_production)::int AS month,
                        {grade_sql}
                    FROM view_geology_ore_details_roa op
                    WHERE op.direct = 'No'
                      AND EXTRACT(YEAR FROM op.tgl_production) = %s
                      {material_clause}
                      {op_iup_clause}
                    GROUP BY EXTRACT(MONTH FROM op.tgl_production)
                )
                SELECT
                    TO_CHAR(TO_DATE(bulan.month::text, 'MM'), 'Mon') AS label,
                    COALESCE(i.total_ore, 0),
                    COALESCE(i.released_ore, 0),
                    COALESCE(i.ni, 0),
                    COALESCE(i.co, 0),
                    COALESCE(i.fe, 0),
                    COALESCE(i.mgo, 0),
                    COALESCE(i.sio2, 0),
                    COALESCE(i.sm, 0)
                FROM bulan
                LEFT JOIN incoming i ON bulan.month = i.month
                ORDER BY bulan.month
            """
            params = [year, *material_params, *op_iup_params]

        elif filter_type == "all":
            query = f"""
                SELECT
                    TO_CHAR(op.tgl_production, 'YYYY') AS label,
                    {grade_sql}
                FROM view_geology_ore_details_roa op
                WHERE op.direct = 'No'
                  {material_clause}
                  {op_iup_clause}
                GROUP BY TO_CHAR(op.tgl_production, 'YYYY')
                ORDER BY TO_CHAR(op.tgl_production, 'YYYY')
            """
            params = [*material_params, *op_iup_params]

        else:
            return JsonResponse({"error": "Invalid filter"}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        x_data = []
        y_total_ore = []
        y_released_ore = []
        y_data_ni = []
        y_data_co = []
        y_data_fe = []
        y_data_mgo = []
        y_data_sio2 = []
        y_data_sm = []

        for row in results:
            x_data.append(str(row[0]).strip())
            y_total_ore.append(round(float(row[1] or 0), 2))
            y_released_ore.append(round(float(row[2] or 0), 2))
            y_data_ni.append(round(float(row[3] or 0), 2))
            y_data_co.append(round(float(row[4] or 0), 2))
            y_data_fe.append(round(float(row[5] or 0), 2))
            y_data_mgo.append(round(float(row[6] or 0), 2))
            y_data_sio2.append(round(float(row[7] or 0), 2))
            y_data_sm.append(round(float(row[8] or 0), 2))

        return JsonResponse({
            "x_data": x_data,
            "y_total_ore": y_total_ore,
            "y_released_ore": y_released_ore,
            "y_data_ni": y_data_ni,
            "y_data_co": y_data_co,
            "y_data_fe": y_data_fe,
            "y_data_mgo": y_data_mgo,
            "y_data_sio2": y_data_sio2,
            "y_data_sm": y_data_sm,
            "material": material or "ALL",
        })

    except DatabaseError as e:
        return JsonResponse({"error": str(e)}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# def get_production_grade(request):
#     try:
#         iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
#         material = request.GET.get("material")  # LIM / SAP / kosong

#         ds, de = resolve_period(request)

#         if not ds or not de:
#             return JsonResponse({"error": "Invalid filter"}, status=400)

#         result = fetch_production_grade(
#             ds=ds,
#             de=de,
#             material=material,
#             iup_filter=iup_filter,
#         )

#         return JsonResponse({
#             "date_start": str(ds),
#             "date_end": str(de),
#             "material": material or "ALL",
#             **result,
#         })

#     except DatabaseError:
#         return JsonResponse({"error": "Database error"}, status=500)

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)