# analytics/services/bot/services/blending_service.py

from django.test import RequestFactory

from geology.views.inventory.inventory_raw import (
    get_data_inventory
)

from analytics.services.bot.utils.response import (
    json_response_to_dict
)


def get_inventory_blending_source(params):
    factory = RequestFactory()

    query = {
        "iup_id": params.get("iup_id"),
        "material": params.get("material"),
        "areaFilter": params.get("stockpile"),
        "page": 1,
    }

    query = {k: v for k, v in query.items() if v not in [None, ""]}

    request = factory.get("/inventory/list/", data=query)
    response = get_data_inventory(request)

    return json_response_to_dict(response)


def rank_blending_candidates(domes, material=None, min_balance=0):
    candidates = []

    for d in domes:
        balance = float(d.get("balance") or 0)
        ni = float(d.get("ni") or 0)

        if balance <= min_balance:
            continue

        # skip dome tanpa grade
        if ni <= 0:
            continue

        if material and d.get("nama_material") != material:
            continue

        candidates.append({
            "stockpile": d.get("stockpile"),
            "pile_id": d.get("pile_id"),
            "material": d.get("nama_material"),
            "balance": round(balance, 2),
            "ni": round(ni, 2),
            "fe": round(float(d.get("fe") or 0), 2),
            "mgo": round(float(d.get("mgo") or 0), 2),
            "sio2": round(float(d.get("sio2") or 0), 2),
            "sm": round(float(d.get("sm") or 0), 2),
        })

    return sorted(
        candidates,
        key=lambda x: (x["ni"], x["balance"]),
        reverse=True
    )


def get_blending_review_service(params):
    inventory = get_inventory_blending_source(params)

    material = params.get("material")
    min_balance = float(params.get("min_balance") or 0)

    domes = inventory.get("data", [])
    candidates = rank_blending_candidates(
        domes=domes,
        material=material,
        min_balance=min_balance
    )

    return {
        "inventory_summary": inventory.get("summary", {}),
        "total_available_domes": len(candidates),
        "top_candidates": candidates[:15],
        "available_domes": candidates,
        "note": (
            "Blending candidates are ranked by Ni and balance. "
            "Final blending ratio should be calculated by backend optimizer."
        )
    }