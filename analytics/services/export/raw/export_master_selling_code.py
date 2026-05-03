import tempfile
from django.core.files import File
from openpyxl import Workbook
from openpyxl.styles import Font

from master.models import SellingCode
from analytics.export_registry import register_exporter

def to_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _safe_attr(obj, attr, default=""):
    try:
        value = getattr(obj, attr, default)
        return value if value is not None else default
    except Exception:
        return default


def _get_iup_code(row):
    if getattr(row, "iup", None):
        return (
            _safe_attr(row.iup, "iup_code")
            or _safe_attr(row.iup, "code")
            or ""
        )
    return ""


def _get_iup_name(row):
    if getattr(row, "iup", None):
        return (
            _safe_attr(row.iup, "iup_name")
            or _safe_attr(row.iup, "name")
            or ""
        )
    return ""


def _get_username(row):
    if getattr(row, "user", None):
        return (
            _safe_attr(row.user, "username")
            or _safe_attr(row.user, "email")
            or ""
        )
    return ""


def _apply_filters(qs, params):
    iup_id = params.get("iup_id") or params.get("iup")
    if iup_id not in (None, "", "null", "undefined"):
        try:
            qs = qs.filter(iup_id=int(iup_id))
        except (TypeError, ValueError):
            pass

    search = params.get("search")
    if search not in (None, "", "null", "undefined"):
        qs = qs.filter(code__icontains=search)

    ordering = params.get("ordering")
    allowed_ordering = {
        "id", "-id",
        "code", "-code",
        "type", "-type",
        "created_at", "-created_at",
    }
    if ordering in allowed_ordering:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("code")

    return qs


@register_exporter("master.selling_code")
def export_master_selling_code(job):
    qs = SellingCode.objects.select_related("iup", "user").all()
    qs = _apply_filters(qs, job.params or {})

    wb = Workbook()
    ws = wb.active
    ws.title = "Selling Code"

    headers = [
        "ID",
        "IUP Code",
        "IUP Name",
        "Code",
        "Type",
        "Description",
        "Active",
        "Truck Factors",
        "Sublot Close",
        "Group Close",
        "Ritase Max",
        "Tonnage",
        "Ni",
        "Fe",
        "Al2O3",
        "Co",
        "MgO",
        "SiO2",
        "CaO",
        "MnO",
        "Cr2O3",
        "SM",
        "MC",
        "Created By",
    ]

    ws.append(headers)

    for col in ws[1]:
        col.font = Font(bold=True)

    for row in qs.iterator(chunk_size=2000):
        ws.append([
            row.id,
            _get_iup_code(row),
            _get_iup_name(row),
            row.code or "",
            row.type or "",
            row.description or "",
            row.active if row.active is not None else "",
            to_float(row.truck_factors),
            row.sublot_close or "",
            row.group_close if row.group_close is not None else "",
            row.ritase_max if row.ritase_max is not None else "",
            to_float(row.tonnage),
            to_float(row.ni),
            to_float(row.fe),
            to_float(row.al2o3),
            to_float(row.co),
            to_float(row.mgo),
            to_float(row.sio2),
            to_float(row.cao),
            to_float(row.mno),
            to_float(row.cr2o3),
            to_float(row.sm),
            to_float(row.mc),
            _get_username(row),
        ])

    # Optional: auto width sederhana
    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            try:
                cell_len = len(str(cell.value or ""))
                if cell_len > max_length:
                    max_length = cell_len
            except Exception:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 30)

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()

    filename = f"selling_code_export_{job.id}.xlsx"
    return File(open(tmp.name, "rb"), name=filename)