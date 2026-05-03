from decimal import Decimal
from django.db.models import Sum
from geology.models import OreProductions


def get_tonnage_by_dome(dome_id: int) -> Decimal:
    result = (
        OreProductions.objects
        .filter(id_pile=dome_id)
        .aggregate(total=Sum("tonnage"))
    )
    return result["total"] or Decimal("0")