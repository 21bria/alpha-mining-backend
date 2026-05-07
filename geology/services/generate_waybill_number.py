from datetime import datetime

from django.db.models import Max

from geology.models.geology_waybills import Waybills


def generate_number(date_delivery):
    date_part = datetime.strptime(
        str(date_delivery),
        "%Y-%m-%d"
    ).strftime("%Y%m%d")

    prefix = f"WB-{date_part}-"

    last = (
        Waybills.objects
        .filter(waybill_number__startswith=prefix)
        .aggregate(max_no=Max("waybill_number"))
    )["max_no"]

    if last:
        try:
            last_number = int(last.split("-")[-1])
        except Exception:
            last_number = 0
    else:
        last_number = 0

    new_number = last_number + 1

    return f"{prefix}{new_number:04d}"