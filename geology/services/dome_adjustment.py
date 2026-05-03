from decimal import Decimal, ROUND_HALF_UP, getcontext
from django.db import transaction
from django.db.models import Sum

from geology.models import OreProductions


def get_tonnage_by_dome(dome_id: int) -> Decimal:
    result = (
        OreProductions.objects
        .filter(id_pile=dome_id)
        .aggregate(total=Sum("tonnage"))
    )
    total = result["total"]

    if total is None:
        return Decimal("0")

    return Decimal(str(total))


def scale_dome_tonnage(dome_id: int, target_total: Decimal) -> tuple[Decimal, Decimal]:
    """
    Scale semua tonnage OreProductions pada dome tertentu
    agar total akhirnya = target_total.

    Return:
        current_total, scale_factor
    """
    getcontext().prec = 18

    qs = OreProductions.objects.filter(id_pile=dome_id).order_by("id")
    current_total = get_tonnage_by_dome(dome_id)

    if current_total <= Decimal("0"):
        raise ValueError(f"Current total dome = 0 untuk dome {dome_id}")

    target_total = Decimal(str(target_total))
    scale_factor = (target_total / current_total).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP
    )

    with transaction.atomic():
        objs = []

        for obj in qs:
            tonnage_decimal = Decimal(str(obj.tonnage or 0))
            obj.tonnage = float(
                (tonnage_decimal * scale_factor).quantize(
                    Decimal("0.000001"),
                    rounding=ROUND_HALF_UP
                )
            )
            objs.append(obj)

        if objs:
            OreProductions.objects.bulk_update(objs, ["tonnage"])

        # koreksi residu kecil supaya total benar-benar sama dengan target_total
        new_total = get_tonnage_by_dome(dome_id)
        delta = (target_total - new_total).quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP
        )

        if abs(delta) > Decimal("0.000001"):
            largest = OreProductions.objects.filter(id_pile=dome_id).order_by("-tonnage", "-id").first()
            if largest:
                largest_tonnage = Decimal(str(largest.tonnage or 0))
                largest.tonnage = float(
                    (largest_tonnage + delta).quantize(
                        Decimal("0.000001"),
                        rounding=ROUND_HALF_UP
                    )
                )
                largest.save(update_fields=["tonnage"])

    return current_total, scale_factor