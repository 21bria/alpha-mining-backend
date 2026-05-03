from django.db import connection
from analytics.services.iup_filter import build_iup_clause

def fetch_fueling_year(year: int, iup_filter=None):
    f_iup_clause, f_iup_params = build_iup_clause(iup_filter, "f")
    t1_iup_clause, t1_iup_params = build_iup_clause(iup_filter, "t1")

    with connection.cursor() as cur:
        # Fuel by Date (Year)
        daily_query = f"""
            WITH bulan AS (
                SELECT
                    TO_CHAR(gs::date, 'YYYY-MM') AS dt,
                    TO_CHAR(gs::date, 'FMMonth') AS bulan_label
                FROM generate_series(
                    make_date(%s, 1, 1),
                    make_date(%s, 12, 31),
                    interval '1 month'
                ) gs
            ),
            actual AS (
                SELECT
                    TO_CHAR(f.date, 'YYYY-MM') AS dt,
                    SUM(f.volume) AS total
                FROM mining_fuel_consumption f
                WHERE EXTRACT(YEAR FROM f.date) = %s
                  {f_iup_clause}
                GROUP BY TO_CHAR(f.date, 'YYYY-MM')
            )
            SELECT
                b.dt AS date,
                b.bulan_label,
                COALESCE(a.total, 0) AS volume
            FROM bulan b
            LEFT JOIN actual a ON b.dt = a.dt
            ORDER BY b.dt
        """
        daily_params = [year, year, year] + f_iup_params

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
            WHERE EXTRACT(YEAR FROM t1.date) = %s
              {t1_iup_clause}
            GROUP BY t3.category
            ORDER BY t3.category
        """
        category_params = [year] + t1_iup_params

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