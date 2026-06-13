from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from analytics.models_report_management import (
    ReportManagementMining,
    ReportManagementMetric,
)


def d(value):
    return Decimal(str(value or 0))


def safe_achievement(actual, plan):
    actual = d(actual)
    plan = d(plan)

    if plan <= 0:
        return Decimal("0")

    return round((actual / plan) * 100, 2)


def get_period_query(report):
    return {
        "iup_id": report.iup_id,
        "filter_type": "range",
        "period_start": report.period_start,
        "period_end": report.period_end,
    }


def get_inventory_query(report):
    return {
        "iup_id": report.iup_id,
        "cut_date": report.period_end,
    }


def pick_summary(data):
    return (
        data.get("range")
        or data.get("weekly")
        or data.get("monthly")
        or data.get("yearly")
        or data.get("summary")
        or {}
    )


def build_material_label(prefix, materials):
    if not materials:
        return prefix

    if prefix == "Waste":
        return f"Waste ({len(materials)} Materials)"

    names = "+".join([str(x.get("material", "")).strip() for x in materials if x.get("material")])
    return f"{prefix} ({names})" if names else prefix


def build_material_description(materials):
    return " • ".join([
        f"{x.get('material')}: {float(x.get('actual') or 0):,.2f}"
        for x in materials
    ])


def sync_report_management(report, user=None):
    """
    Sync ReportManagement draft from live source.

    Important:
    - Only use this for Draft report.
    - Published report should be locked and not synced.
    """

    if report.status != "Draft":
        raise ValueError("Only draft report can be synchronized.")

    from analytics.views.management.get_production import get_summary_management
    from analytics.views.management.get_barging import get_barging_management
    from analytics.views.management.get_inventory import get_inventory_management

    query = get_period_query(report)
    inventory_query = get_inventory_query(report)

    mining_data = get_summary_management(**query)
    barging_data = get_barging_management(**query)
    inventory_data = get_inventory_management(**inventory_query)

    mining_summary = pick_summary(mining_data)
    barging_summary = pick_summary(barging_data)
    inventory_summary = inventory_data.get("summary") or {}

    ore_materials = mining_summary.get("ore_materials") or []
    non_ore_materials = mining_summary.get("non_ore_materials") or []

    ore_label = build_material_label("Ore", ore_materials)
    waste_label = build_material_label("Waste", non_ore_materials)

    ore_description = build_material_description(ore_materials)
    waste_description = build_material_description(non_ore_materials)

    total_ore_plan = d(mining_summary.get("total_ore_plan"))
    total_ore = d(mining_summary.get("total_ore"))

    total_non_ore_plan = d(mining_summary.get("total_non_ore_plan"))
    total_non_ore = d(mining_summary.get("total_non_ore"))

    total_barging_plan = d(barging_summary.get("total_plan"))
    total_barging = d(barging_summary.get("total_barging"))

    total_production = total_ore + total_non_ore
    total_movement = total_production + total_barging

    total_inventory = d(inventory_summary.get("total_balance"))
    avg_ni = d(inventory_summary.get("avg_ni"))
    stockpile_count = int(inventory_summary.get("stockpile_count") or 0)

    inventory_description = (
        f"{stockpile_count} Stockpiles • Avg Ni {avg_ni}%"
    )

    hse_metric = report.metrics.filter(section="HSE").order_by("sort_order").first()
    hse_incidents = int(hse_metric.value) if hse_metric else 0

    mining_rows = [
        {
            "material": ore_label,
            "description": ore_description,
            "plan": total_ore_plan,
            "actual": total_ore,
            "achievement": safe_achievement(total_ore, total_ore_plan),
            "status": "STABLE",
            "group": "ORE",
            "is_total": False,
            "is_grand_total": False,
            "source_module": "AUTO",
            "sort_order": 1,
        },
        {
            "material": waste_label,
            "description": waste_description,
            "plan": total_non_ore_plan,
            "actual": total_non_ore,
            "achievement": safe_achievement(total_non_ore, total_non_ore_plan),
            "status": "STABLE",
            "group": "WASTE",
            "is_total": False,
            "is_grand_total": False,
            "source_module": "AUTO",
            "sort_order": 2,
        },
        {
            "material": "Barging",
            "description": (
                f"LIM: {float(barging_summary.get('total_lim') or 0):,.2f} • "
                f"SAP: {float(barging_summary.get('total_sap') or 0):,.2f}"
            ),
            "plan": total_barging_plan,
            "actual": total_barging,
            "achievement": safe_achievement(total_barging, total_barging_plan),
            "status": "STABLE",
            "group": "BARGING",
            "is_total": False,
            "is_grand_total": False,
            "source_module": "AUTO",
            "sort_order": 3,
        },
        {
            "material": "SUB-TOTAL",
            "plan": total_ore_plan + total_non_ore_plan,
            "actual": total_production,
            "achievement": safe_achievement(
                total_production,
                total_ore_plan + total_non_ore_plan,
            ),
            "status": "STABLE",
            "group": "TOTAL",
            "is_total": True,
            "is_grand_total": False,
            "source_module": "AUTO",
            "sort_order": 900,
        },
        {
            "material": "TOTAL",
            "plan": total_ore_plan + total_non_ore_plan + total_barging_plan,
            "actual": total_movement,
            "achievement": safe_achievement(
                total_movement,
                total_ore_plan + total_non_ore_plan + total_barging_plan,
            ),
            "status": "STABLE",
            "group": "TOTAL",
            "is_total": True,
            "is_grand_total": True,
            "source_module": "AUTO",
            "sort_order": 999,
        },
    ]

    inventory_metric = {
        "section": "INVENTORY",
        "title": "Inventory",
        "value": total_inventory,
        "suffix": "t",
        "description": inventory_description,
        "source_module": "AUTO",
        "sort_order": 5,
    }

    with transaction.atomic():
        report.mining_rows.filter(source_module="AUTO").delete()
        ReportManagementMining.objects.bulk_create([
            ReportManagementMining(report=report, **row)
            for row in mining_rows
        ])

        report.metrics.filter(section="INVENTORY", source_module="AUTO").delete()
        ReportManagementMetric.objects.create(
            report=report,
            **inventory_metric,
        )

        report.hse_incidents = hse_incidents
        report.total_production = total_production
        report.total_barging = total_barging
        report.total_movement = total_movement
        report.total_inventory = total_inventory
        report.avg_ni = avg_ni
        report.stockpile_count = stockpile_count
        report.last_synced_at = timezone.now()
        report.save()

    return report