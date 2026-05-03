# mining/services/production_summary.py
from django.db.models import Sum
from decimal import Decimal


def apply_common_filters(qs, params):
    iup_id               = params.get("iup_id") or params.get("iup")
    loading_point        = params.get("loading_point")
    dumping_point        = params.get("dumping_point")
    date_production_from = params.get("date_production_from")
    date_production_to   = params.get("date_production_to")

    if iup_id:
        qs = qs.filter(iup_id=iup_id)

    if loading_point:
        qs = qs.filter(loading_point__iexact=loading_point)

    if dumping_point:
        qs = qs.filter(dumping_point__iexact=dumping_point)

    if date_production_from:
        qs = qs.filter(date_production__gte=date_production_from)

    if date_production_to:
        qs = qs.filter(date_production__lte=date_production_to)

    return qs


def sum_tonnage(qs, field_name="tonnage"):
    return qs.aggregate(total=Sum(field_name))["total"] or Decimal("0")