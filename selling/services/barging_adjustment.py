from decimal import Decimal
from django.db.models import Sum

from selling.models import SellingBarging


def get_barging_totals_by_code(code_lot: str) -> dict:
    code_lot = str(code_lot).strip()

    result = (
        SellingBarging.objects
        .filter(code_lot__iexact=code_lot)
        .aggregate(
            total_tonnage=Sum("tonnage"),
            total_ritase=Sum("ritase_group"),
        )
    )

    return {
        "tonnage": Decimal(str(result["total_tonnage"])) if result["total_tonnage"] is not None else Decimal("0"),
        "ritase": int(result["total_ritase"]) if result["total_ritase"] is not None else 0,
    }