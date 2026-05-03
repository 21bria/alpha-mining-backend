import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db import transaction
from django.db.models.functions import Lower

from master.models import (
    MineIUP, 
    Material,
    StockFactories,
    SourceMinesDome,
    SourceMinesDumping,
    BargeUnits,
    BargePort,
    MineUnits
    )

from selling.models import SellingBarging
from imports.utils.parsers import norm, parse_flexible_date, parse_flexible_time
from imports.utils.converters import to_nullable_float, to_nullable_int
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def clean_numeric(value: Any) -> float | None:
    try:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
            value = re.sub(r"[^0-9.<>-]", "", value)
            if value.startswith("<") or value.startswith(">"):
                value = value[1:]

        return to_nullable_float(value)
    except Exception:
        return None


def build_selling_code(iup_code: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{iup_code}-{ts}"

@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class SellingBargeImporter:
    """
    Importer untuk tabel SellingBarging
    style mengikuti importer baru:
    1. validate + collect
    2. resolve master
    3. build objects
    4. bulk create
    """

    DATE_FIELDS = [
        "date_hauling",
        "date_barging_in",
        "date_barging_load",
        "date_barging_out",
    ]

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()
        parsed: list[dict[str, Any]] = []

        today = date.today()

        iup_codes_needed: set[str] = set()
        material_names_needed: set[str] = set()
        pile_names_needed: set[str] = set()
        stockpile_names_needed: set[str] = set()
        factory_names_needed: set[str] = set()
        barge_codes_needed: set[str] = set()
        port_names_needed: set[str] = set()
        unit_code_needed: set[str] = set()

        # =========================================================
        # 1. VALIDATE + COLLECT
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(row.get("iup_code"))

                date_hauling = parse_flexible_date(row.get("date_hauling"))
                date_barging_in = parse_flexible_date(row.get("date_barging_in"))
                date_barging_load = parse_flexible_date(row.get("date_barging_load"))
                date_barging_out = parse_flexible_date(row.get("date_barging_out"))
                time_hauling = parse_flexible_time(row.get("time"))

                shift = upper_or_none(row.get("shift"))
                material_name = norm_or_none(row.get("material"))
                dome_ori_name = norm_or_none(row.get("dome_ori"))
                stockpile_name = norm_or_none(row.get("stockpile"))
                buyer_name = norm_or_none(row.get("buyer"))
                barge_code = norm_or_none(row.get("barge_code"))
                barge_load_loc = norm_or_none(row.get("barge_load_loc"))
                barge_unload_loc = norm_or_none(row.get("barge_unload_loc"))

                sale_code = upper_or_none(row.get("sale_code"))
                code_lot = norm_or_none(row.get("code_lot"))
                sub_lot = norm_or_none(row.get("sub_lot"))
                unit_code = norm_or_none(row.get("no_truck"))
                group_value = norm_or_none(row.get("group"))
                adjust_sale = upper_or_none(row.get("adjust_sale"))
                direct = norm_or_none(row.get("direct"))
                tonnage = clean_numeric(row.get("tonnage"))

                required_fields = {
                    "iup_code": iup_code,
                    "date_barging_in": date_barging_in,
                    "date_hauling": date_hauling,
                    "date_barging_load": date_barging_load,
                    "date_barging_out": date_barging_out,
                    "shift": shift,
                    "material": material_name,
                    "sale_code": sale_code,
                    "code_lot": code_lot,
                    "sub_lot": sub_lot,
                }

                missing_fields = [
                    field_name for field_name, value in required_fields.items() if not value
                ]
                if missing_fields:
                    raise ValueError("required fields missing: " + ", ".join(missing_fields))

                # validasi tanggal tidak boleh > hari ini
                for field_name, field_value in {
                    "date_hauling": date_hauling,
                    "date_barging_in": date_barging_in,
                    "date_barging_load": date_barging_load,
                    "date_barging_out": date_barging_out,
                }.items():
                    if field_value and field_value > today:
                        raise ValueError(
                            f"{field_name} '{field_value}' cannot be greater than today '{today}'"
                        )

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "date_hauling": date_hauling,
                    "date_barging_in": date_barging_in,
                    "date_barging_load": date_barging_load,
                    "date_barging_out": date_barging_out,
                    "time_hauling": time_hauling,
                    "shift": shift,
                    "material_name": material_name,
                    "dome_ori_name": dome_ori_name,
                    "stockpile_name": stockpile_name,
                    "buyer_name": buyer_name,
                    "barge_code": barge_code,
                    "barge_load_loc": barge_load_loc,
                    "barge_unload_loc": barge_unload_loc,
                    "sale_code": sale_code,
                    "code_lot": code_lot,
                    "sub_lot": sub_lot,
                    "unit_code": unit_code,
                    "group_value": group_value,
                    "adjust_sale": adjust_sale,
                    "direct": direct,
                    "tonnage": tonnage,
                })

                iup_codes_needed.add(iup_code.casefold())
                if material_name:
                    material_names_needed.add(material_name.casefold())
                if dome_ori_name:
                    pile_names_needed.add(dome_ori_name.casefold())
                if stockpile_name:
                    stockpile_names_needed.add(stockpile_name.casefold())
                if buyer_name:
                    factory_names_needed.add(buyer_name.casefold())
                if barge_code:
                    barge_codes_needed.add(barge_code.casefold())
                if barge_load_loc:
                    port_names_needed.add(barge_load_loc.casefold())
                if barge_unload_loc:
                    port_names_needed.add(barge_unload_loc.casefold())
                if unit_code:
                    unit_code_needed.add(unit_code.casefold()) 

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # =========================================================
        # 2. RESOLVE MASTER DATA
        # =========================================================
        iup_map = {
            code_l: obj_id
            for code_l, obj_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }

        material_map = {
            name_l: obj_id
            for name_l, obj_id in (
                Material.objects
                .annotate(name_l=Lower("name"))
                .filter(name_l__in=material_names_needed)
                .values_list("name_l", "id")
            )
        }

        pile_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SourceMinesDome.objects
                .annotate(name_l=Lower("pile_id"))
                .filter(name_l__in=pile_names_needed)
                .values_list("name_l", "id")
            )
        }

        stockpile_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SourceMinesDumping.objects
                .annotate(name_l=Lower("dumping_point"))
                .filter(name_l__in=stockpile_names_needed)
                .values_list("name_l", "id")
            )
        }

        factory_map = {
            name_l: obj_id
            for name_l, obj_id in (
                StockFactories.objects
                .annotate(name_l=Lower("factory_stock"))
                .filter(name_l__in=factory_names_needed)
                .values_list("name_l", "id")
            )
        }

        barge_map = {
            code_l: obj_id
            for code_l, obj_id in (
                BargeUnits.objects
                .annotate(code_l=Lower("barge_code"))
                .filter(code_l__in=barge_codes_needed)
                .values_list("code_l", "id")
            )
        }

        port_map = {
            name_l: port_name
            for name_l, port_name in (
                BargePort.objects
                .annotate(name_l=Lower("port_name"))
                .filter(name_l__in=port_names_needed)
                .values_list("name_l", "port_name")
            )
        }

        # untuk mapping material code khusus adjust_sale
        material_code_map = {
            name_l: obj_id
            for name_l, obj_id in (
                Material.objects
                .annotate(name_l=Lower("name"))
                .filter(name_l__in={"sap", "lim"})
                .values_list("name_l", "id")
            )
        }

        unit_map = {
            vendor_l: obj_id
            for vendor_l, obj_id in (
                MineUnits.objects
                .annotate(vendor_l=Lower("unit_vendor"))
                .filter(vendor_l__in=unit_code_needed)
                .values_list("vendor_l", "unit_vendor")
            )
        }


        # =========================================================
        # 3. BUILD OBJECTS
        # =========================================================
        to_create: list[SellingBarging] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                errors = []

                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    errors.append(f"iup_code '{item['iup_code']}' not found")

                material_id = (
                    material_map.get(item["material_name"].casefold())
                    if item["material_name"] else None
                )
                pile_id = (
                    pile_map.get(item["dome_ori_name"].casefold())
                    if item["dome_ori_name"] else None
                )
                stockpile_id = (
                    stockpile_map.get(item["stockpile_name"].casefold())
                    if item["stockpile_name"] else None
                )
                factory_id = (
                    factory_map.get(item["buyer_name"].casefold())
                    if item["buyer_name"] else None
                )
                barge_id = (
                    barge_map.get(item["barge_code"].casefold())
                    if item["barge_code"] else None
                )

                validated_load_loc = (
                    port_map.get(item["barge_load_loc"].casefold())
                    if item["barge_load_loc"] else None
                )
                validated_unload_loc = (
                    port_map.get(item["barge_unload_loc"].casefold())
                    if item["barge_unload_loc"] else None
                )
                validate_unit = (
                    unit_map.get(item["unit_code"].casefold())
                    if item["unit_code"] else None
                )

                if item["material_name"] and material_id is None:
                    errors.append(f"material '{item['material_name']}' not found")
                if item["dome_ori_name"] and pile_id is None:
                    errors.append(f"dome_ori '{item['dome_ori_name']}' not found")
                if item["stockpile_name"] and stockpile_id is None:
                    errors.append(f"stockpile '{item['stockpile_name']}' not found")
                if item["buyer_name"] and factory_id is None:
                    errors.append(f"buyer '{item['buyer_name']}' not found")
                if item["barge_code"] and barge_id is None:
                    errors.append(f"barge_code '{item['barge_code']}' not found")
                # if item["barge_load_loc"] and validated_load_loc is None:
                #     errors.append(f"barge_load_loc '{item['barge_load_loc']}' not found")
                # if item["barge_unload_loc"] and validated_unload_loc is None:
                #     errors.append(f"barge_unload_loc '{item['barge_unload_loc']}' not found")
                if item["unit_code"] and validate_unit is None:
                    errors.append(f"unit_code '{item['unit_code']}' not found")

                if errors:
                    raise ValueError("; ".join(errors))

                # =========================
                # business logic lama
                # =========================
                type_selling = item["sale_code"]
                adjust_sale = item["adjust_sale"]
                code_lot = item["code_lot"]
                batch = item["sub_lot"]
                group_value = item["group_value"] or ""

                if adjust_sale == "RKEF":
                    material_code_name = "SAP"
                    type_selling = "SAS"
                    type_monitoring = "SAS_CKS"
                elif adjust_sale == "HPAL":
                    material_code_name = "LIM"
                    type_selling = "LIS"
                    type_monitoring = "LIS_CKS"
                else:
                    material_code_name = (item["material_name"] or "").upper()
                    type_monitoring = f"{type_selling}_CKS"

                material_code_id = material_code_map.get(material_code_name.casefold())
                if material_code_id is None and material_code_name:
                    # fallback ambil dari material asli
                    material_code_id = material_id or 0

                code_batch_in = f"{type_selling}{material_code_id or ''}{code_lot or ''}{batch or ''}"
                code_monitoring = f"{type_monitoring}{material_code_id or ''}{code_lot or ''}{batch or ''}{group_value}"
                code_batch_ex = f"{type_selling}{material_code_id or ''}Split_CAR{code_lot or ''}{batch or ''}"
                code_batch_pulp = f"{type_selling}{code_lot or ''}Split_CAR{batch or ''}"

                code = build_selling_code(item["iup_code"])

                obj = SellingBarging(
                    iup_id=iup_id,
                    code=code,
                    date_barge_in=item["date_barging_in"],
                    date_hauling=item["date_hauling"],
                    time_hauling=item["time_hauling"],
                    shift=item["shift"],
                    date_barging=item["date_barging_load"],
                    barge_code=barge_id,
                    barging_load_loc=validated_load_loc,
                    barging_unload_loc=validated_unload_loc,
                    unit_code=item["unit_code"],
                    type_selling=type_selling,
                    id_material=material_id,
                    id_pile=pile_id,
                    id_stockpile=stockpile_id,
                    id_factory=factory_id,
                    tonnage=item["tonnage"],
                    batch=batch,
                    code_inc=group_value,
                    code_sub=batch,
                    code_batch_in=code_batch_in,
                    code_batch_ex=code_batch_ex,
                    code_batch_pulp=code_batch_pulp,
                    code_monitoring=code_monitoring,
                    code_lot=code_lot,
                    date_barge_out=item["date_barging_out"],
                    sale_adjust=adjust_sale,
                    direct=item["direct"],
                    sale_dome="Continue",
                    user=user,
                )
                to_create.append(obj)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 4. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                SellingBarging.objects.bulk_create(to_create, batch_size=300)
            res.success += len(to_create)

        return res