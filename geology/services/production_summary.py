# geology/services/production_summary.py
from django.db.models import Sum
from decimal import Decimal


def apply_common_filters(qs, params):
    iup_id = params.get("iup_id") or params.get("iup")
    material = params.get("material")
    prospect_area = params.get("prospect_area")
    sampling_area = params.get("sampling_area")
    pile_id = params.get("pile_id")
    tgl_from = params.get("tgl_production_from")
    tgl_to = params.get("tgl_production_to")

    if iup_id:
        qs = qs.filter(iup_id=iup_id)

    if material:
        materials = [x.strip() for x in str(material).split(",") if x.strip()]
        if materials:
            qs = qs.filter(nama_material__in=materials)

    if prospect_area:
        qs = qs.filter(prospect_area__iexact=prospect_area)

    if sampling_area:
        qs = qs.filter(stockpile__iexact=sampling_area)

    if pile_id:
        qs = qs.filter(pile_id__iexact=pile_id)

    if tgl_from:
        qs = qs.filter(tgl_production__gte=tgl_from)

    if tgl_to:
        qs = qs.filter(tgl_production__lte=tgl_to)

    return qs


def sum_tonnage(qs, field_name="tonnage"):
    return qs.aggregate(total=Sum(field_name))["total"] or Decimal("0")