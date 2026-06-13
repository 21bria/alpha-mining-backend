from decimal import Decimal

from django.test import RequestFactory

from analytics.views.management.get_production import get_summary_management
from analytics.views.management.get_barging import get_barging_management
from analytics.views.management.get_inventory import get_inventory_management


def d(value):
    return Decimal(str(value or 0))


def safe_achievement(actual, plan):
    actual = d(actual)
    plan = d(plan)

    if plan <= 0:
        return Decimal("0")

    return round((actual / plan) * 100, 2)


def pick_summary(data):
    return (
        data.get("range")
        or data.get("weekly")
        or data.get("monthly")
        or data.get("yearly")
        or data.get("wtd")
        or data.get("mtd")
        or data.get("ytd")
        or data.get("summary")
        or {}
    )


def json_response_to_dict(response):
    import json

    if hasattr(response, "content"):
        return json.loads(response.content.decode("utf-8"))

    return response or {}


def call_view_as_dict(view_func, query):
    factory = RequestFactory()
    request = factory.get("/", data=query)
    response = view_func(request)
    return json_response_to_dict(response)


def build_live_query(
    *,
    iup_id,
    period_type,
    year=None,
    month=None,
    week=None,
    period_start=None,
    period_end=None,
):
    query = {
        "iup_id": iup_id,
        "filter_type": period_type,
        "year": year,
        "yearly": year,
        "month": month,
        "monthly": month,
        "week": week,
        "weekly": week,
        "period_start": period_start,
        "period_end": period_end,
        "date_start": period_start,
        "date_end": period_end,
    }

    return {
        key: value
        for key, value in query.items()
        if value not in [None, ""]
    }


def build_inventory_query(*, iup_id, period_end=None, period_start=None):
    cut_date = period_end or period_start

    return {
        key: value
        for key, value in {
            "iup_id": iup_id,
            "cut_date": cut_date,
            "date": cut_date,
        }.items()
        if value not in [None, ""]
    }

def status_from_plan(actual, plan):
    actual = d(actual)
    plan = d(plan)

    if plan <= 0:
        return "STABLE" if actual <= 0 else "UP"

    if actual >= plan:
        return "UP"

    return "DOWN"


def build_material_label(prefix, materials):
    if not materials:
        return prefix

    if prefix == "Waste":
        return f"Waste ({len(materials)} Materials)"

    names = "+".join([
        str(x.get("material", "")).strip()
        for x in materials
        if x.get("material")
    ])

    return f"{prefix} ({names})" if names else prefix


def build_live_management_report(
    *,
    iup_id,
    period_type,
    year=None,
    month=None,
    week=None,
    period_start=None,
    period_end=None,
):
    """
    Live preview data untuk Management Report.
    Dipakai kalau report belum ada atau period_type=range.

    Catatan:
    Ini sementara memanggil view function via RequestFactory.
    Nanti lebih bagus dipecah jadi service/helper asli.
    """

    period_type = (period_type or "range").lower()

    query = build_live_query(
        iup_id=iup_id,
        period_type=period_type,
        year=year,
        month=month,
        week=week,
        period_start=period_start,
        period_end=period_end,
    )

    inventory_query = build_inventory_query(
        iup_id=iup_id,
        period_start=period_start,
        period_end=period_end,
    )

    mining_data = call_view_as_dict(get_summary_management, query)
    barging_data = call_view_as_dict(get_barging_management, query)
    inventory_data = call_view_as_dict(get_inventory_management, inventory_query)

    mining_summary = pick_summary(mining_data)
    barging_summary = pick_summary(barging_data)
    inventory_summary = inventory_data.get("summary") or {}

    ore_materials = mining_summary.get("ore_materials") or []
    non_ore_materials = mining_summary.get("non_ore_materials") or []

    ore_plan = d(mining_summary.get("total_ore_plan"))
    ore_actual = d(mining_summary.get("total_ore"))

    waste_plan = d(mining_summary.get("total_non_ore_plan"))
    waste_actual = d(mining_summary.get("total_non_ore"))

    barging_plan = d(barging_summary.get("total_plan"))
    barging_actual = d(barging_summary.get("total_barging"))

    production_plan = ore_plan + waste_plan
    production_actual = ore_actual + waste_actual

    total_plan = production_plan + barging_plan
    total_actual = production_actual + barging_actual

    inventory_balance = d(inventory_summary.get("total_balance"))
    avg_ni = d(inventory_summary.get("avg_ni"))
    stockpile_count = int(inventory_summary.get("stockpile_count") or 0)

    mining_rows = [
        {
            "id": None,
            "material": build_material_label("Ore", ore_materials),
            "group": "ORE",
            "plan": ore_plan,
            "actual": ore_actual,
            "achievement": safe_achievement(ore_actual, ore_plan),
            "status": status_from_plan(ore_actual, ore_plan),
            "is_total": False,
            "is_grand_total": False,
            "source_module": "LIVE",
            "sort_order": 1,
        },
        {
            "id": None,
            "material": build_material_label("Waste", non_ore_materials),
            "group": "WASTE",
            "plan": waste_plan,
            "actual": waste_actual,
            "achievement": safe_achievement(waste_actual, waste_plan),
            "status": status_from_plan(waste_actual, waste_plan),
            "is_total": False,
            "is_grand_total": False,
            "source_module": "LIVE",
            "sort_order": 2,
        },
        {
            "id": None,
            "material": "Barging",
            "group": "BARGING",
            "plan": barging_plan,
            "actual": barging_actual,
            "achievement": safe_achievement(barging_actual, barging_plan),
            "status": status_from_plan(barging_actual, barging_plan),
            "is_total": False,
            "is_grand_total": False,
            "source_module": "LIVE",
            "sort_order": 3,
        },
        {
            "id": None,
            "material": "SUB-TOTAL",
            "group": "TOTAL",
            "plan": production_plan,
            "actual": production_actual,
            "achievement": safe_achievement(production_actual, production_plan),
            "status": status_from_plan(production_actual, production_plan),
            "is_total": True,
            "is_grand_total": False,
            "source_module": "LIVE",
            "sort_order": 900,
        },
        {
            "id": None,
            "material": "TOTAL",
            "group": "TOTAL",
            "plan": total_plan,
            "actual": total_actual,
            "achievement": safe_achievement(total_actual, total_plan),
            "status": status_from_plan(total_actual, total_plan),
            "is_total": True,
            "is_grand_total": True,
            "source_module": "LIVE",
            "sort_order": 999,
        },
    ]

    metrics = [
        {
            "id": None,
            "section": "INVENTORY",
            "title": "Inventory",
            "value": inventory_balance,
            "suffix": "t",
            "description": f"{stockpile_count} Stockpiles • Avg Ni {avg_ni}%",
            "source_module": "LIVE",
            "sort_order": 1,
        }
    ]

    return {
        "id": None,
        "iup": int(iup_id) if iup_id else None,
        "period_type": period_type,
        "year": int(year) if year else None,
        "month": int(month) if month else None,
        "week": int(week) if week else None,
        "period_start": period_start,
        "period_end": period_end,
        "status": "Live",
        "report_code": "LIVE-PREVIEW",
        "title": "Live Management Preview",

        "summary_cards": [],
        "notes": {},
        "remarks": "",

        "mining_rows": mining_rows,
        "metrics": metrics,
        "manpower_rows": [],
        "documents": [],

        "hse_incidents": 0,
        "total_production": production_actual,
        "total_barging": barging_actual,
        "total_movement": total_actual,
        "total_inventory": inventory_balance,
        "avg_ni": avg_ni,
        "stockpile_count": stockpile_count,
    }