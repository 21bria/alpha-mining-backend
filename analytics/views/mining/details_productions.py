# views.py
import logging
from django.http import JsonResponse
from django.db import connection
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from django.utils.timezone import now
logger = logging.getLogger(__name__) 

def safe_division(numerator, denominator):
    return round(numerator / denominator * 100, 0) if denominator else 0

# For Chart
def get_detail_material(request):
    iup_filter   = request.GET.get("iup_id")
    filter_type  = request.GET.get("filter_type")
    filter_year  = int(request.GET.get("year", 0))
    filter_month = int(request.GET.get("month", 0))
    filter_week  = request.GET.get("week")
    filter_date  = request.GET.get("filter_date")
    date_start   = request.GET.get("date_start")
    date_end     = request.GET.get("date_end")

    if filter_type == "monthly" and filter_year and filter_month:
        return get_detail_monthly(filter_year, filter_month, iup_filter)

    elif filter_type == "daily" and filter_date:
        return get_detail_daily(filter_date, iup_filter)

    elif filter_type == "range" and date_start and date_end:
        return get_detail_range(date_start, date_end, iup_filter)

    elif filter_type == "yearly" and filter_year:
        return get_detail_yearly(filter_year, iup_filter)

    elif filter_type == "weekly" and filter_week:
        return get_detail_weekly(filter_week, iup_filter)

    elif filter_type == "all":
        return get_detail_all(iup_filter)

    else:
        return JsonResponse({"error": "Invalid filter"}, status=400)
    
def get_detail_daily(filter_date, iup_filter=None):
    where_actual = "mp.date_production = %s::date"
    where_plan = "p.date_plan = %s::date"

    actual_params = [filter_date]
    plan_params = [filter_date]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND mp.iup_id IN ({placeholders})"
            where_plan += f" AND p.iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

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

        hour_series AS (
            SELECT
                make_time(hour_label, 0, 0) AS raw_time,
                TO_CHAR(make_time(hour_label, 0, 0), 'HH24') AS left_time,
                hour_label,
                sort_order
            FROM working_hours
        ),

        actual_detail AS (
            SELECT
                LPAD(mp.t_load::text, 2, '0') AS left_time,
                COALESCE(mp.categories_material, 'Other') AS material_group,
                mp.nama_material AS material_name,
                SUM(mp.tonnage)::numeric AS tonnage
            FROM view_mining_productions mp
            WHERE {where_actual}
            GROUP BY
                LPAD(mp.t_load::text, 2, '0'),
                COALESCE(mp.categories_material, 'Other'),
                mp.nama_material
        ),

        actual_total AS (
            SELECT
                left_time,
                SUM(tonnage)::numeric AS total
            FROM actual_detail
            GROUP BY left_time
        ),

        plan_detail AS (
            SELECT
                COALESCE(p.categories_material, 'Other') AS material_group,
                p.material_name AS material_name,
                ROUND((COALESCE(SUM(p.tonnage), 0) / 22)::numeric, 2) AS plan_tonnage
            FROM view_mining_plan_productions p
            WHERE {where_plan}
            GROUP BY
                COALESCE(p.categories_material, 'Other'),
                p.material_name
        ),

        plan_per_hour AS (
            SELECT
                ROUND((COALESCE(SUM(plan_tonnage), 0))::numeric, 2) AS plan_data
            FROM plan_detail
        )

        SELECT
            hs.hour_label AS id,
            hs.left_time,

            ad.material_group,
            ad.material_name,
            COALESCE(ad.tonnage, 0)::numeric AS tonnage,

            pd.material_group AS plan_material_group,
            pd.material_name AS plan_material_name,
            COALESCE(pd.plan_tonnage, 0)::numeric AS plan_tonnage,

            COALESCE(at.total, 0)::numeric AS total,
            COALESCE(pph.plan_data, 0)::numeric AS plan_data

        FROM hour_series hs
        LEFT JOIN actual_detail ad
            ON hs.left_time = ad.left_time
        LEFT JOIN actual_total at
            ON hs.left_time = at.left_time
        CROSS JOIN plan_per_hour pph
        LEFT JOIN plan_detail pd
            ON 1 = 1
        ORDER BY
            hs.sort_order,
            ad.material_group,
            ad.material_name,
            pd.material_group,
            pd.material_name;
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "left_time",
            "material_group",
            "material_name",
            "tonnage",
            "plan_material_group",
            "plan_material_name",
            "plan_tonnage",
            "total",
            "plan_data",
        ],
    )

    for col in ["tonnage", "plan_tonnage", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    hour_df = df[["id", "left_time", "total", "plan_data"]].drop_duplicates("left_time")
    hour_df = hour_df.sort_values("id")

    x_data = hour_df["left_time"].tolist()
    total_actual = hour_df["total"].round(1).astype(float).tolist()
    total_plan = hour_df["plan_data"].round(1).astype(float).tolist()

    achievement = []
    for _, r in hour_df.iterrows():
        achievement.append(
            round((r["total"] / r["plan_data"] * 100), 1)
            if r["plan_data"] > 0
            else 0.0
        )

    # ACTUAL series
    series_groups = {}

    detail_df = df[df["material_name"].notna()].copy()

    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        series_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["left_time"]): float(r["tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(x, 0.0), 1)
                    for x in x_data
                ],
            })

    # PLAN series per material
    series_plan_groups = {}

    plan_detail_df = df[df["plan_material_name"].notna()].copy()

    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        series_plan_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("plan_material_name"):
            material_key = str(material_name or "-")

            # daily plan per material sama untuk semua jam
            plan_value = float(mat_df["plan_tonnage"].iloc[0] or 0)

            series_plan_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(plan_value, 1)
                    for _ in x_data
                ],
            })

    plan_sum = float(hour_df["plan_data"].sum())
    total_sum = float(hour_df["total"].sum())

    group_totals = {}
    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        group_totals[group_key] = round(float(group_df["tonnage"].sum()), 1)

    plan_group_totals = {}
    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        # plan_tonnage sudah per jam, grand plan = sum semua jam
        plan_group_totals[group_key] = round(
            float(group_df.drop_duplicates("plan_material_name")["plan_tonnage"].sum()) * len(x_data),
            1,
        )

    material_totals = {}
    for material_name, mat_df in detail_df.groupby("material_name"):
        material_key = str(material_name or "-")
        material_totals[material_key] = round(float(mat_df["tonnage"].sum()), 1)

    plan_material_totals = {}
    for material_name, mat_df in plan_detail_df.groupby("plan_material_name"):
        material_key = str(material_name or "-")
        plan_material_totals[material_key] = round(
            float(mat_df["plan_tonnage"].iloc[0]) * len(x_data),
            1,
        )

    grand_total = {
        "total": round(total_sum, 1),
        "plan": round(plan_sum, 1),
        "achievement": round((total_sum / plan_sum * 100), 1) if plan_sum > 0 else 0.0,
        "avg": round(float(hour_df["total"].mean()), 1) if not hour_df.empty else 0.0,
        "groups": group_totals,
        "plan_groups": plan_group_totals,
        "materials": material_totals,
        "plan_materials": plan_material_totals,
    }

    return JsonResponse({
        "x_data": x_data,
        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": achievement,
        "series_groups": series_groups,
        "series_plan_groups": series_plan_groups,
        "grand_total": grand_total,
    }, safe=False)

def get_detail_monthly(filter_year, filter_month, iup_filter=None):
    year = int(filter_year)
    month = int(filter_month)

    last_day = calendar.monthrange(year, month)[1]
    tgl_pertama = datetime(year, month, 1).date()
    tgl_terakhir = datetime(year, month, last_day).date()

    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [tgl_pertama, tgl_terakhir]
    plan_params = [tgl_pertama, tgl_terakhir]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params.extend(iup_ids)
            plan_params.extend(iup_ids)

    query = f"""
        WITH day_series AS (
            SELECT generate_series(
                %s::date,
                %s::date,
                interval '1 day'
            )::date AS left_date
        ),

        actual_detail AS (
            SELECT
                DATE(date_production) AS left_date,
                COALESCE(categories_material, 'Other') AS material_group,
                nama_material AS material_name,
                SUM(tonnage)::numeric AS tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY
                DATE(date_production),
                COALESCE(categories_material, 'Other'),
                nama_material
        ),

        actual_total AS (
            SELECT
                left_date,
                SUM(tonnage)::numeric AS total
            FROM actual_detail
            GROUP BY left_date
        ),

        plan_detail AS (
            SELECT
                DATE(date_plan) AS left_date,
                COALESCE(categories_material, 'Other') AS material_group,
                material_name,
                SUM(tonnage)::numeric AS plan_tonnage
            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY
                DATE(date_plan),
                COALESCE(categories_material, 'Other'),
                material_name
        ),

        plan_total AS (
            SELECT
                left_date,
                SUM(plan_tonnage)::numeric AS plan_data
            FROM plan_detail
            GROUP BY left_date
        )

        SELECT
            EXTRACT(DAY FROM ds.left_date)::int AS id,
            ds.left_date::date AS date_value,

            ad.material_group,
            ad.material_name,
            COALESCE(ad.tonnage, 0)::numeric AS tonnage,

            pd.material_group AS plan_material_group,
            pd.material_name AS plan_material_name,
            COALESCE(pd.plan_tonnage, 0)::numeric AS plan_tonnage,

            COALESCE(at.total, 0)::numeric AS total,
            COALESCE(pt.plan_data, 0)::numeric AS plan_data

        FROM day_series ds
        LEFT JOIN actual_detail ad
            ON ds.left_date = ad.left_date
        LEFT JOIN actual_total at
            ON ds.left_date = at.left_date
        LEFT JOIN plan_total pt
            ON ds.left_date = pt.left_date
        LEFT JOIN plan_detail pd
            ON ds.left_date = pd.left_date
        ORDER BY
            ds.left_date,
            ad.material_group,
            ad.material_name,
            pd.material_group,
            pd.material_name;
    """

    params = [
        tgl_pertama,
        tgl_terakhir,
        *actual_params,
        *plan_params,
    ]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "date_value",
            "material_group",
            "material_name",
            "tonnage",
            "plan_material_group",
            "plan_material_name",
            "plan_tonnage",
            "total",
            "plan_data",
        ],
    )

    for col in ["tonnage", "plan_tonnage", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    day_df = df[["id", "date_value", "total", "plan_data"]].drop_duplicates("id")
    day_df = day_df.sort_values("id")

    x_data = day_df["id"].astype(int).tolist()
    total_actual = day_df["total"].round(1).astype(float).tolist()
    total_plan = day_df["plan_data"].round(1).astype(float).tolist()

    achievement = []
    for _, r in day_df.iterrows():
        achievement.append(
            round((r["total"] / r["plan_data"] * 100), 1)
            if r["plan_data"] > 0
            else 0.0
        )

    # ACTUAL
    detail_df = df[df["material_name"].notna()].copy()
    series_groups = {}

    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        series_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("material_name"):
            material_key = str(material_name or "-")

            map_data = {
                int(r["id"]): float(r["tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(day, 0.0), 1)
                    for day in x_data
                ],
            })

    # PLAN
    plan_detail_df = df[df["plan_material_name"].notna()].copy()
    series_plan_groups = {}

    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        series_plan_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("plan_material_name"):
            material_key = str(material_name or "-")

            map_data = {
                int(r["id"]): float(r["plan_tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_plan_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(day, 0.0), 1)
                    for day in x_data
                ],
            })

    total_sum = float(day_df["total"].sum())
    plan_sum = float(day_df["plan_data"].sum())

    group_totals = {}
    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        group_totals[group_key] = round(float(group_df["tonnage"].sum()), 1)

    plan_group_totals = {}
    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        plan_group_totals[group_key] = round(float(group_df["plan_tonnage"].sum()), 1)

    material_totals = {}
    for material_name, mat_df in detail_df.groupby("material_name"):
        material_key = str(material_name or "-")
        material_totals[material_key] = round(float(mat_df["tonnage"].sum()), 1)

    plan_material_totals = {}
    for material_name, mat_df in plan_detail_df.groupby("plan_material_name"):
        material_key = str(material_name or "-")
        plan_material_totals[material_key] = round(float(mat_df["plan_tonnage"].sum()), 1)

    grand_total = {
        "total": round(total_sum, 1),
        "plan": round(plan_sum, 1),
        "achievement": round((total_sum / plan_sum * 100), 1) if plan_sum > 0 else 0.0,
        "avg": round(float(day_df["total"].mean(skipna=True)), 1) if not day_df.empty else 0.0,
        "groups": group_totals,
        "plan_groups": plan_group_totals,
        "materials": material_totals,
        "plan_materials": plan_material_totals,
    }

    return JsonResponse({
        "x_data": x_data,
        "total_tonnage": total_actual,
        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": achievement,
        "series_groups": series_groups,
        "series_plan_groups": series_plan_groups,
        "grand_total": grand_total,
    }, safe=False)

def get_detail_weekly(filter_week, iup_filter=None):
    iso_year, iso_week = map(int, filter_week.split("-"))

    start_date = date.fromisocalendar(iso_year, iso_week, 1)
    end_date = date.fromisocalendar(iso_year, iso_week, 7)

    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [start_date, end_date]
    plan_params = [start_date, end_date]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH day_series AS (
            SELECT generate_series(
                %s::date,
                %s::date,
                interval '1 day'
            )::date AS left_date
        ),

        actual_detail AS (
            SELECT
                DATE(date_production) AS left_date,
                COALESCE(categories_material, 'Other') AS material_group,
                nama_material AS material_name,
                SUM(tonnage)::numeric AS tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY
                DATE(date_production),
                COALESCE(categories_material, 'Other'),
                nama_material
        ),

        actual_total AS (
            SELECT
                left_date,
                SUM(tonnage)::numeric AS total
            FROM actual_detail
            GROUP BY left_date
        ),

        plan_detail AS (
            SELECT
                DATE(date_plan) AS left_date,
                COALESCE(categories_material, 'Other') AS material_group,
                material_name,
                SUM(tonnage)::numeric AS plan_tonnage
            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY
                DATE(date_plan),
                COALESCE(categories_material, 'Other'),
                material_name
        ),

        plan_total AS (
            SELECT
                left_date,
                SUM(plan_tonnage)::numeric AS plan_data
            FROM plan_detail
            GROUP BY left_date
        )

        SELECT
            TO_CHAR(ds.left_date, 'YYYY-MM-DD') AS tanggal,
            TO_CHAR(ds.left_date, 'FMDy') AS hari,

            ad.material_group,
            ad.material_name,
            COALESCE(ad.tonnage, 0)::numeric AS tonnage,

            pd.material_group AS plan_material_group,
            pd.material_name AS plan_material_name,
            COALESCE(pd.plan_tonnage, 0)::numeric AS plan_tonnage,

            COALESCE(at.total, 0)::numeric AS total,
            COALESCE(pt.plan_data, 0)::numeric AS plan_data

        FROM day_series ds
        LEFT JOIN actual_detail ad
            ON ds.left_date = ad.left_date
        LEFT JOIN actual_total at
            ON ds.left_date = at.left_date
        LEFT JOIN plan_total pt
            ON ds.left_date = pt.left_date
        LEFT JOIN plan_detail pd
            ON ds.left_date = pd.left_date
        ORDER BY
            ds.left_date,
            ad.material_group,
            ad.material_name,
            pd.material_group,
            pd.material_name;
    """

    params = [
        start_date,
        end_date,
        *actual_params,
        *plan_params,
    ]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "tanggal",
            "hari",
            "material_group",
            "material_name",
            "tonnage",
            "plan_material_group",
            "plan_material_name",
            "plan_tonnage",
            "total",
            "plan_data",
        ],
    )

    for col in ["tonnage", "plan_tonnage", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    day_df = df[["tanggal", "hari", "total", "plan_data"]].drop_duplicates("tanggal")
    day_df = day_df.sort_values("tanggal")

    x_keys = day_df["tanggal"].astype(str).tolist()
    x_data = day_df["hari"].astype(str).tolist()

    total_actual = day_df["total"].round(1).astype(float).tolist()
    total_plan = day_df["plan_data"].round(1).astype(float).tolist()

    achievement = []
    for _, r in day_df.iterrows():
        achievement.append(
            round((r["total"] / r["plan_data"] * 100), 1)
            if r["plan_data"] > 0
            else 0.0
        )

    # ACTUAL
    detail_df = df[df["material_name"].notna()].copy()
    series_groups = {}

    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        series_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["tanggal"]): float(r["tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(tanggal, 0.0), 1)
                    for tanggal in x_keys
                ],
            })

    # PLAN
    plan_detail_df = df[df["plan_material_name"].notna()].copy()
    series_plan_groups = {}

    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        series_plan_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("plan_material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["tanggal"]): float(r["plan_tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_plan_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(tanggal, 0.0), 1)
                    for tanggal in x_keys
                ],
            })

    total_sum = float(day_df["total"].sum())
    plan_sum = float(day_df["plan_data"].sum())

    group_totals = {}
    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        group_totals[group_key] = round(float(group_df["tonnage"].sum()), 1)

    plan_group_totals = {}
    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        plan_group_totals[group_key] = round(float(group_df["plan_tonnage"].sum()), 1)

    material_totals = {}
    for material_name, mat_df in detail_df.groupby("material_name"):
        material_key = str(material_name or "-")
        material_totals[material_key] = round(float(mat_df["tonnage"].sum()), 1)

    plan_material_totals = {}
    for material_name, mat_df in plan_detail_df.groupby("plan_material_name"):
        material_key = str(material_name or "-")
        plan_material_totals[material_key] = round(float(mat_df["plan_tonnage"].sum()), 1)

    grand_total = {
        "total": round(total_sum, 1),
        "plan": round(plan_sum, 1),
        "achievement": round((total_sum / plan_sum * 100), 1) if plan_sum > 0 else 0.0,
        "avg": round(float(day_df["total"].mean(skipna=True)), 1) if not day_df.empty else 0.0,
        "groups": group_totals,
        "plan_groups": plan_group_totals,
        "materials": material_totals,
        "plan_materials": plan_material_totals,
    }

    return JsonResponse({
        "x_data": x_data,
        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": achievement,
        "series_groups": series_groups,
        "series_plan_groups": series_plan_groups,
        "grand_total": grand_total,
    }, safe=False)

def get_detail_range(date_start, date_end, iup_filter=None):
    where_actual = "date_production BETWEEN %s AND %s"
    where_plan = "date_plan BETWEEN %s AND %s"

    actual_params = [date_start, date_end]
    plan_params = [date_start, date_end]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))

            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"

            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH day_series AS (
            SELECT generate_series(
                %s::date,
                %s::date,
                interval '1 day'
            )::date AS left_date
        ),

        actual_detail AS (
            SELECT
                DATE(date_production) AS left_date,
                COALESCE(categories_material, 'Other') AS material_group,
                nama_material AS material_name,
                SUM(tonnage)::numeric AS tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY
                DATE(date_production),
                COALESCE(categories_material, 'Other'),
                nama_material
        ),

        actual_total AS (
            SELECT
                left_date,
                SUM(tonnage)::numeric AS total
            FROM actual_detail
            GROUP BY left_date
        ),

        plan_detail AS (
            SELECT
                DATE(date_plan) AS left_date,
                COALESCE(categories_material, 'Other') AS material_group,
                material_name,
                SUM(tonnage)::numeric AS plan_tonnage
            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY
                DATE(date_plan),
                COALESCE(categories_material, 'Other'),
                material_name
        ),

        plan_total AS (
            SELECT
                left_date,
                SUM(plan_tonnage)::numeric AS plan_data
            FROM plan_detail
            GROUP BY left_date
        )

        SELECT
            TO_CHAR(ds.left_date, 'YYYY-MM-DD') AS tanggal,

            ad.material_group,
            ad.material_name,
            COALESCE(ad.tonnage, 0)::numeric AS tonnage,

            pd.material_group AS plan_material_group,
            pd.material_name AS plan_material_name,
            COALESCE(pd.plan_tonnage, 0)::numeric AS plan_tonnage,

            COALESCE(at.total, 0)::numeric AS total,
            COALESCE(pt.plan_data, 0)::numeric AS plan_data

        FROM day_series ds
        LEFT JOIN actual_detail ad
            ON ds.left_date = ad.left_date
        LEFT JOIN actual_total at
            ON ds.left_date = at.left_date
        LEFT JOIN plan_total pt
            ON ds.left_date = pt.left_date
        LEFT JOIN plan_detail pd
            ON ds.left_date = pd.left_date
        ORDER BY
            ds.left_date,
            ad.material_group,
            ad.material_name,
            pd.material_group,
            pd.material_name;
    """

    params = [
        date_start,
        date_end,
        *actual_params,
        *plan_params,
    ]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "tanggal",
            "material_group",
            "material_name",
            "tonnage",
            "plan_material_group",
            "plan_material_name",
            "plan_tonnage",
            "total",
            "plan_data",
        ],
    )

    for col in ["tonnage", "plan_tonnage", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    day_df = df[["tanggal", "total", "plan_data"]].drop_duplicates("tanggal")
    day_df = day_df.sort_values("tanggal")

    x_data = day_df["tanggal"].astype(str).tolist()
    total_actual = day_df["total"].round(1).astype(float).tolist()
    total_plan = day_df["plan_data"].round(1).astype(float).tolist()

    achievement = []
    for _, r in day_df.iterrows():
        achievement.append(
            round((r["total"] / r["plan_data"] * 100), 1)
            if r["plan_data"] > 0
            else 0.0
        )

    # ACTUAL
    detail_df = df[df["material_name"].notna()].copy()
    series_groups = {}

    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        series_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["tanggal"]): float(r["tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(tanggal, 0.0), 1)
                    for tanggal in x_data
                ],
            })

    # PLAN
    plan_detail_df = df[df["plan_material_name"].notna()].copy()
    series_plan_groups = {}

    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        series_plan_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("plan_material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["tanggal"]): float(r["plan_tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_plan_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(tanggal, 0.0), 1)
                    for tanggal in x_data
                ],
            })

    total_sum = float(day_df["total"].sum())
    plan_sum = float(day_df["plan_data"].sum())

    group_totals = {}
    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        group_totals[group_key] = round(float(group_df["tonnage"].sum()), 1)

    plan_group_totals = {}
    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        plan_group_totals[group_key] = round(float(group_df["plan_tonnage"].sum()), 1)

    material_totals = {}
    for material_name, mat_df in detail_df.groupby("material_name"):
        material_key = str(material_name or "-")
        material_totals[material_key] = round(float(mat_df["tonnage"].sum()), 1)

    plan_material_totals = {}
    for material_name, mat_df in plan_detail_df.groupby("plan_material_name"):
        material_key = str(material_name or "-")
        plan_material_totals[material_key] = round(float(mat_df["plan_tonnage"].sum()), 1)

    grand_total = {
        "total": round(total_sum, 1),
        "plan": round(plan_sum, 1),
        "achievement": round((total_sum / plan_sum * 100), 1) if plan_sum > 0 else 0.0,
        "avg": round(float(day_df["total"].mean(skipna=True)), 1) if not day_df.empty else 0.0,
        "groups": group_totals,
        "plan_groups": plan_group_totals,
        "materials": material_totals,
        "plan_materials": plan_material_totals,
    }

    return JsonResponse({
        "x_data": x_data,
        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": achievement,
        "series_groups": series_groups,
        "series_plan_groups": series_plan_groups,
        "grand_total": grand_total,
    }, safe=False)

def get_detail_yearly(yearly, iup_filter=None):
    where_actual = "EXTRACT(YEAR FROM date_production) = %s"
    where_plan = "EXTRACT(YEAR FROM date_plan) = %s"

    actual_params = [yearly]
    plan_params = [yearly]

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH month_series AS (
            SELECT TO_CHAR(
                DATE_TRUNC('month', (DATE %s + (n || ' month')::interval)),
                'YYYY-MM'
            ) AS bulan
            FROM generate_series(0, 11) AS n
        ),

        actual_detail AS (
            SELECT
                TO_CHAR(date_production, 'YYYY-MM') AS bulan,
                COALESCE(categories_material, 'Other') AS material_group,
                nama_material AS material_name,
                SUM(tonnage)::numeric AS tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY
                TO_CHAR(date_production, 'YYYY-MM'),
                COALESCE(categories_material, 'Other'),
                nama_material
        ),

        actual_total AS (
            SELECT
                bulan,
                SUM(tonnage)::numeric AS total
            FROM actual_detail
            GROUP BY bulan
        ),

        plan_detail AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY-MM') AS bulan,
                COALESCE(categories_material, 'Other') AS material_group,
                material_name,
                SUM(tonnage)::numeric AS plan_tonnage
            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY
                TO_CHAR(date_plan, 'YYYY-MM'),
                COALESCE(categories_material, 'Other'),
                material_name
        ),

        plan_total AS (
            SELECT
                bulan,
                SUM(plan_tonnage)::numeric AS plan_data
            FROM plan_detail
            GROUP BY bulan
        )

        SELECT
            ms.bulan,

            ad.material_group,
            ad.material_name,
            COALESCE(ad.tonnage, 0)::numeric AS tonnage,

            pd.material_group AS plan_material_group,
            pd.material_name AS plan_material_name,
            COALESCE(pd.plan_tonnage, 0)::numeric AS plan_tonnage,

            COALESCE(at.total, 0)::numeric AS total,
            COALESCE(pt.plan_data, 0)::numeric AS plan_data

        FROM month_series ms
        LEFT JOIN actual_detail ad
            ON ms.bulan = ad.bulan
        LEFT JOIN actual_total at
            ON ms.bulan = at.bulan
        LEFT JOIN plan_total pt
            ON ms.bulan = pt.bulan
        LEFT JOIN plan_detail pd
            ON ms.bulan = pd.bulan
        ORDER BY
            ms.bulan,
            ad.material_group,
            ad.material_name,
            pd.material_group,
            pd.material_name;
    """

    params = [
        f"{yearly}-01-01",
        *actual_params,
        *plan_params,
    ]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "bulan",
            "material_group",
            "material_name",
            "tonnage",
            "plan_material_group",
            "plan_material_name",
            "plan_tonnage",
            "total",
            "plan_data",
        ],
    )

    for col in ["tonnage", "plan_tonnage", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    month_df = df[["bulan", "total", "plan_data"]].drop_duplicates("bulan")
    month_df = month_df.sort_values("bulan")

    x_keys = month_df["bulan"].astype(str).tolist()
    x_data = [
        datetime.strptime(x, "%Y-%m").strftime("%b %y")
        for x in x_keys
    ]

    total_actual = month_df["total"].round(1).astype(float).tolist()
    total_plan = month_df["plan_data"].round(1).astype(float).tolist()

    achievement = []
    for _, r in month_df.iterrows():
        achievement.append(
            round((r["total"] / r["plan_data"] * 100), 1)
            if r["plan_data"] > 0
            else 0.0
        )

    # ACTUAL
    detail_df = df[df["material_name"].notna()].copy()
    series_groups = {}

    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        series_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["bulan"]): float(r["tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(bulan, 0.0), 1)
                    for bulan in x_keys
                ],
            })

    # PLAN
    plan_detail_df = df[df["plan_material_name"].notna()].copy()
    series_plan_groups = {}

    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        series_plan_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("plan_material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["bulan"]): float(r["plan_tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_plan_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(bulan, 0.0), 1)
                    for bulan in x_keys
                ],
            })

    total_sum = float(month_df["total"].sum())
    plan_sum = float(month_df["plan_data"].sum())

    group_totals = {}
    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        group_totals[group_key] = round(float(group_df["tonnage"].sum()), 1)

    plan_group_totals = {}
    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        plan_group_totals[group_key] = round(float(group_df["plan_tonnage"].sum()), 1)

    material_totals = {}
    for material_name, mat_df in detail_df.groupby("material_name"):
        material_key = str(material_name or "-")
        material_totals[material_key] = round(float(mat_df["tonnage"].sum()), 1)

    plan_material_totals = {}
    for material_name, mat_df in plan_detail_df.groupby("plan_material_name"):
        material_key = str(material_name or "-")
        plan_material_totals[material_key] = round(float(mat_df["plan_tonnage"].sum()), 1)

    grand_total = {
        "total": round(total_sum, 1),
        "plan": round(plan_sum, 1),
        "achievement": round((total_sum / plan_sum * 100), 1) if plan_sum > 0 else 0.0,
        "avg": round(float(month_df["total"].mean(skipna=True)), 1) if not month_df.empty else 0.0,
        "groups": group_totals,
        "plan_groups": plan_group_totals,
        "materials": material_totals,
        "plan_materials": plan_material_totals,
    }

    return JsonResponse({
        "x_data": x_data,
        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": achievement,
        "series_groups": series_groups,
        "series_plan_groups": series_plan_groups,
        "grand_total": grand_total,
    }, safe=False)

def get_detail_all(iup_filter=None):
    where_actual = "1=1"
    where_plan = "1=1"

    actual_params = []
    plan_params = []

    if iup_filter:
        iup_ids = [x.strip() for x in str(iup_filter).split(",") if x.strip()]
        if iup_ids:
            placeholders = ",".join(["%s"] * len(iup_ids))
            where_actual += f" AND iup_id IN ({placeholders})"
            where_plan += f" AND iup_id IN ({placeholders})"
            actual_params += iup_ids
            plan_params += iup_ids

    query = f"""
        WITH actual_detail AS (
            SELECT
                TO_CHAR(date_production, 'YYYY') AS tahun,
                COALESCE(categories_material, 'Other') AS material_group,
                nama_material AS material_name,
                SUM(tonnage)::numeric AS tonnage
            FROM view_mining_productions
            WHERE {where_actual}
            GROUP BY
                TO_CHAR(date_production, 'YYYY'),
                COALESCE(categories_material, 'Other'),
                nama_material
        ),

        actual_total AS (
            SELECT
                tahun,
                SUM(tonnage)::numeric AS total
            FROM actual_detail
            GROUP BY tahun
        ),

        plan_detail AS (
            SELECT
                TO_CHAR(date_plan, 'YYYY') AS tahun,
                COALESCE(categories_material, 'Other') AS material_group,
                material_name,
                SUM(tonnage)::numeric AS plan_tonnage
            FROM view_mining_plan_productions
            WHERE {where_plan}
            GROUP BY
                TO_CHAR(date_plan, 'YYYY'),
                COALESCE(categories_material, 'Other'),
                material_name
        ),

        plan_total AS (
            SELECT
                tahun,
                SUM(plan_tonnage)::numeric AS plan_data
            FROM plan_detail
            GROUP BY tahun
        ),

        year_series AS (
            SELECT tahun FROM actual_total
            UNION
            SELECT tahun FROM plan_total
        )

        SELECT
            ys.tahun,

            ad.material_group,
            ad.material_name,
            COALESCE(ad.tonnage, 0)::numeric AS tonnage,

            pd.material_group AS plan_material_group,
            pd.material_name AS plan_material_name,
            COALESCE(pd.plan_tonnage, 0)::numeric AS plan_tonnage,

            COALESCE(at.total, 0)::numeric AS total,
            COALESCE(pt.plan_data, 0)::numeric AS plan_data

        FROM year_series ys
        LEFT JOIN actual_detail ad
            ON ys.tahun = ad.tahun
        LEFT JOIN actual_total at
            ON ys.tahun = at.tahun
        LEFT JOIN plan_total pt
            ON ys.tahun = pt.tahun
        LEFT JOIN plan_detail pd
            ON ys.tahun = pd.tahun
        ORDER BY
            ys.tahun,
            ad.material_group,
            ad.material_name,
            pd.material_group,
            pd.material_name;
    """

    params = actual_params + plan_params

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "tahun",
            "material_group",
            "material_name",
            "tonnage",
            "plan_material_group",
            "plan_material_name",
            "plan_tonnage",
            "total",
            "plan_data",
        ],
    )

    for col in ["tonnage", "plan_tonnage", "total", "plan_data"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    year_df = df[["tahun", "total", "plan_data"]].drop_duplicates("tahun")
    year_df = year_df.sort_values("tahun")

    x_data = year_df["tahun"].astype(str).tolist()
    total_actual = year_df["total"].round(1).astype(float).tolist()
    total_plan = year_df["plan_data"].round(1).astype(float).tolist()

    achievement = []
    for _, r in year_df.iterrows():
        achievement.append(
            round((r["total"] / r["plan_data"] * 100), 1)
            if r["plan_data"] > 0
            else 0.0
        )

    # ACTUAL
    detail_df = df[df["material_name"].notna()].copy()
    series_groups = {}

    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        series_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["tahun"]): float(r["tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(tahun, 0.0), 1)
                    for tahun in x_data
                ],
            })

    # PLAN
    plan_detail_df = df[df["plan_material_name"].notna()].copy()
    series_plan_groups = {}

    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        series_plan_groups[group_key] = []

        for material_name, mat_df in group_df.groupby("plan_material_name"):
            material_key = str(material_name or "-")

            map_data = {
                str(r["tahun"]): float(r["plan_tonnage"] or 0)
                for _, r in mat_df.iterrows()
            }

            series_plan_groups[group_key].append({
                "name": material_key,
                "data": [
                    round(map_data.get(tahun, 0.0), 1)
                    for tahun in x_data
                ],
            })

    total_sum = float(year_df["total"].sum())
    plan_sum = float(year_df["plan_data"].sum())

    group_totals = {}
    for group_name, group_df in detail_df.groupby("material_group"):
        group_key = str(group_name or "Other")
        group_totals[group_key] = round(float(group_df["tonnage"].sum()), 1)

    plan_group_totals = {}
    for group_name, group_df in plan_detail_df.groupby("plan_material_group"):
        group_key = str(group_name or "Other")
        plan_group_totals[group_key] = round(float(group_df["plan_tonnage"].sum()), 1)

    material_totals = {}
    for material_name, mat_df in detail_df.groupby("material_name"):
        material_key = str(material_name or "-")
        material_totals[material_key] = round(float(mat_df["tonnage"].sum()), 1)

    plan_material_totals = {}
    for material_name, mat_df in plan_detail_df.groupby("plan_material_name"):
        material_key = str(material_name or "-")
        plan_material_totals[material_key] = round(float(mat_df["plan_tonnage"].sum()), 1)

    grand_total = {
        "total": round(total_sum, 1),
        "plan": round(plan_sum, 1),
        "achievement": round((total_sum / plan_sum * 100), 1) if plan_sum > 0 else 0.0,
        "avg": round(float(year_df["total"].mean(skipna=True)), 1) if not year_df.empty else 0.0,
        "groups": group_totals,
        "plan_groups": plan_group_totals,
        "materials": material_totals,
        "plan_materials": plan_material_totals,
    }

    return JsonResponse({
        "x_data": x_data,
        "total_actual": total_actual,
        "total_plan": total_plan,
        "achievement": achievement,
        "series_groups": series_groups,
        "series_plan_groups": series_plan_groups,
        "grand_total": grand_total,
    }, safe=False)