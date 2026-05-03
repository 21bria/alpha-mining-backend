import os
import tempfile
from openpyxl import Workbook
from openpyxl.styles import numbers
from django.core.files import File
from django.db.models import Q
from datetime import datetime, time

from mining.models import planProductions
from analytics.export_registry import register_exporter

def excel_safe_datetime(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    return value


def excel_safe_time(value):
    if isinstance(value, time):
        return value.replace(tzinfo=None) if value.tzinfo else value
    return value

def _apply_filters(qs, params):
    iup_id = params.get("iup_id") or params.get("iup")
    if iup_id not in (None, "", "null", "undefined"):
        try:
            qs = qs.filter(iup_id=int(iup_id))
        except (TypeError, ValueError):
            pass

    tgl_from = params.get("date_start")
    if tgl_from not in (None, "", "null", "undefined"):
        qs = qs.filter(date_plan__gte=tgl_from)

    tgl_to = params.get("date_end")
    if tgl_to not in (None, "", "null", "undefined"):
        qs = qs.filter(date_plan__lte=tgl_to)

    search = params.get("search")
    if search not in (None, "", "null", "undefined"):
        qs = qs.filter(
            Q(date_plan__icontains=search) |
            Q(iup_code__icontains=search) |
            Q(iup_name__icontains=search)
        )

    ordering = params.get("ordering")
    allowed_ordering = {"id", "-id", "date_plan", "-date_plan"}
    if ordering in allowed_ordering:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("date_plan")

    return qs


@register_exporter("mining.plan_productions")
def export_mining_plan_productions(job):
    qs = planProductions.objects.select_related("iup", "user").all()
    qs = _apply_filters(qs, job.params or {})

    wb = Workbook()
    ws = wb.active
    ws.title = "Mining Plan Productions"

    # HEADER
    ws.append([
        "IUP Code",
        "IUP Name",
        "Date Plan",
        "Category",
        "Sources",
        "Vendors",
        "Topsoil",
        "OB",
        "LGLO",
        "MGLO",
        "HGLO",
        "Waste",
        "MWS",
        "LGSO",
        "UGLO",
        "MGSO",
        "HGSO",
        "LIM",
        "SAP",
        "Quarry",
        "Ballast",
        "Biomass",
        "Ref Plan",
        "Task ID",
        "Created At",
        "Username",
    ])

    # DATA
    for row in qs.iterator(chunk_size=2000):
        ws.append([
            getattr(row.iup, "iup_code", "") or "",
            getattr(row.iup, "iup_name", "") or "",
            row.date_plan if row.date_plan else None,
            row.category or "",
            row.sources or "",
            row.vendors or "",
            float(row.topsoil or 0),
            float(row.ob or 0),
            float(row.lglo or 0),
            float(row.mglo or 0),
            float(row.hglo or 0),
            float(row.waste or 0),
            float(row.mws or 0),
            float(row.lgso or 0),
            float(row.uglo or 0),
            float(row.mgso or 0),
            float(row.hgso or 0),
            float(row.lim or 0),
            float(row.sap or 0),
            float(row.quarry or 0),
            float(row.ballast or 0),
            float(row.biomass or 0),
            row.ref_plan or "",
            row.task_id or "",
            excel_safe_datetime(row.created_at) if getattr(row, "created_at", None) else None,
            getattr(row.user, "username", "") or "",
        ])

    # FORMAT DATE (kolom 3)
    for row_idx in range(2, ws.max_row + 1):
        cell = ws.cell(row=row_idx, column=3)
        if cell.value:
            cell.number_format = "YYYY-MM-DD"

    # FORMAT DATETIME (Created At kolom 25)
    for row_idx in range(2, ws.max_row + 1):
        cell = ws.cell(row=row_idx, column=25)
        if cell.value:
            cell.number_format = "YYYY-MM-DD HH:MM:SS"

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()

    filename = f"mining_plan_productions_export_{job.id}.xlsx"
    return File(open(tmp.name, "rb"), name=filename)