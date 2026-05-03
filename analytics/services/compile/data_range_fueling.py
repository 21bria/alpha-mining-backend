
# /services.py
from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def g(row, key):
    return row.get(key, 0) or 0

def fetch_fueling_to_date(ds: str, de: str, iup_filter=None):
    f_iup_clause, f_iup_params = build_iup_clause(iup_filter, "f")
    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")

    with connection.cursor() as cur:
        # Fuel by Date (Daily)
        daily_query = f"""
            WITH day_series AS (
                SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS dt
            ),
            actual AS (
                SELECT
                    f.date::date AS dt,
                    SUM(f.volume) AS total
                FROM mining_fuel_consumption f
                WHERE f.date BETWEEN %s AND %s
                  {f_iup_clause}
                GROUP BY f.date::date
            )
            SELECT
                ds.dt AS date,
                COALESCE(a.total, 0) AS volume
            FROM day_series ds
            LEFT JOIN actual a ON ds.dt = a.dt
            ORDER BY ds.dt
        """
        daily_params = [ds, de, ds, de] + f_iup_params

        cur.execute(daily_query, daily_params)
        daily_rows = [
            dict(zip([c[0] for c in cur.description], r))
            for r in cur.fetchall()
        ]

        daily_total = sum(r["volume"] or 0 for r in daily_rows)

        # Fuel by Category
        category_query = f"""
            SELECT
                COALESCE(TRIM(t3.category), 'Unknown') AS category,
                ROUND(SUM(t1.volume)::NUMERIC, 2) AS volume
            FROM mining_fuel_consumption t1
            LEFT JOIN master_units t2
                ON t2.unit_code::text = t1.unit::text
            LEFT JOIN master_units_categories t3
                ON t3.id = t2.id_category
            WHERE t1.date BETWEEN %s AND %s
              {t1_iup_clause}
            GROUP BY t3.category
            ORDER BY t3.category
        """
        category_params = [ds, de] + t1_iup_params

        cur.execute(category_query, category_params)
        category_rows = [
            dict(zip([c[0] for c in cur.description], r))
            for r in cur.fetchall()
        ]
        category_total = sum(r["volume"] or 0 for r in category_rows)

    return {
        "daily": {
            "series": daily_rows,
            "total": daily_total
        },
        "category": {
            "series": category_rows,
            "total": category_total
        }
    }
