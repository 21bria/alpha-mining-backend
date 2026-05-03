from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from master.models import MineUnits, UnitAssignment, unitsCategories, Vendors
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def normalize_code(value: Any) -> str:
    s = norm(value).upper()
    return s.replace("_", "-").replace(" ", "-")


def build_unit_vendor(unit_code: Any, vendor_code: Any) -> str:
    u = normalize_code(unit_code)
    v = normalize_code(vendor_code)
    if not u:
        return ""
    if not v:
        return u
    return f"{u}-{v}"


def parse_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "active"}:
        return True
    if s in {"0", "false", "no", "n", "inactive"}:
        return False
    return default


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MineUnitImporter:
    """
    Import master unit + optional assignment

    Minimum:
    - unit_code
    - vendors   -> dipakai untuk resolve vendor.code lalu membentuk unit_vendor

    Optional unit:
    - unit_model
    - unit_type / unit_class
    - brand
    - category
    - supports
    - description
    - commisioning_date
    - on_hire
    - off_hire
    - status

    Optional assignment:
    - iup_code
    - start_date
    - end_date
    - active
    """

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        parsed: list[dict[str, Any]] = []
        seen_unit_vendors: set[str] = set()

        category_names_needed: set[str] = set()
        vendor_names_needed: set[str] = set()
        iup_codes_needed: set[str] = set()

        today = date.today()

        # =========================================================
        # 1. VALIDATE + COLLECT
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                unit_code = normalize_code(row.get("unit_code"))
                unit_model = norm_or_none(row.get("unit_model"))
                unit_class = norm_or_none(row.get("unit_type")) or norm_or_none(row.get("unit_class"))
                brand = norm_or_none(row.get("brand"))
                category_name = norm_or_none(row.get("category"))
                vendor_name = norm_or_none(row.get("vendors"))
                supports = norm_or_none(row.get("supports"))
                description = norm_or_none(row.get("description"))

                commisioning_date = parse_flexible_date(row.get("commisioning_date"))
                on_hire = parse_flexible_date(row.get("on_hire"))
                off_hire = parse_flexible_date(row.get("off_hire"))

                iup_code = upper_or_none(row.get("iup_code"))
                start_date = parse_flexible_date(row.get("start_date"))
                end_date = parse_flexible_date(row.get("end_date"))
                active = parse_bool(row.get("active"), default=True)

                status_raw = row.get("status")
                status = 1 if status_raw in (None, "") else int(status_raw)

                if not unit_code:
                    raise ValueError("unit_code is required")

                if not vendor_name:
                    raise ValueError("vendors is required")

                # validasi tanggal unit
                for field_name, field_value in {
                    "commisioning_date": commisioning_date,
                    "on_hire": on_hire,
                    "off_hire": off_hire,
                }.items():
                    if field_value and field_value > today:
                        raise ValueError(
                            f"{field_name} '{field_value}' cannot be greater than today '{today}'"
                        )

                if on_hire and off_hire and off_hire < on_hire:
                    raise ValueError("off_hire cannot be earlier than on_hire")

                # validasi assignment optional
                has_assignment_data = bool(iup_code or start_date or end_date or row.get("active") is not None)

                if has_assignment_data:
                    if not iup_code:
                        raise ValueError("iup_code is required when assignment columns are used")
                    if not start_date:
                        raise ValueError("start_date is required when assignment columns are used")
                    if end_date and end_date < start_date:
                        raise ValueError("end_date cannot be earlier than start_date")

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "unit_code": unit_code,
                    "unit_model": unit_model,
                    "unit_class": unit_class,
                    "brand": brand,
                    "category_name": category_name,
                    "vendor_name": vendor_name,
                    "supports": supports,
                    "description": description,
                    "commisioning_date": commisioning_date,
                    "on_hire": on_hire,
                    "off_hire": off_hire,
                    "status": status,
                    "iup_code": iup_code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "active": active,
                    "has_assignment_data": has_assignment_data,
                })

                if category_name:
                    category_names_needed.add(category_name.casefold())
                if vendor_name:
                    vendor_names_needed.add(vendor_name.casefold())
                if iup_code:
                    iup_codes_needed.add(iup_code.casefold())

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # =========================================================
        # 2. RESOLVE MASTER DATA
        # =========================================================
        category_map = {
            name_l: obj_id
            for name_l, obj_id in (
                unitsCategories.objects
                .annotate(name_l=Lower("category"))
                .filter(name_l__in=category_names_needed)
                .values_list("name_l", "id")
            )
        }

        vendor_map = {
            name_l: {
                "id": obj_id,
                "code": code,
                "vendor_name": vendor_name,
            }
            for name_l, obj_id, code, vendor_name in (
                Vendors.objects
                .annotate(name_l=Lower("vendor_name"))
                .filter(name_l__in=vendor_names_needed)
                .values_list("name_l", "id", "code", "vendor_name")
            )
        }

        iup_map = {
            code_l: obj_id
            for code_l, obj_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }

        # =========================================================
        # 3. PREPARE EXISTING CHECK
        # =========================================================
        parsed_unit_vendor_keys: set[str] = set()
        prepared_items: list[dict[str, Any]] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                errors = []

                vendor_obj = vendor_map.get(item["vendor_name"].casefold()) if item["vendor_name"] else None
                if item["vendor_name"] and vendor_obj is None:
                    errors.append(f"vendors '{item['vendor_name']}' not found")
                elif vendor_obj and not vendor_obj["code"]:
                    errors.append(f"vendor '{vendor_obj['vendor_name']}' has empty code")

                id_category = (
                    category_map.get(item["category_name"].casefold())
                    if item["category_name"] else None
                )
                if item["category_name"] and id_category is None:
                    errors.append(f"category '{item['category_name']}' not found")

                iup_id = None
                if item["has_assignment_data"]:
                    iup_id = iup_map.get(item["iup_code"].casefold()) if item["iup_code"] else None
                    if item["iup_code"] and iup_id is None:
                        errors.append(f"iup_code '{item['iup_code']}' not found")

                if errors:
                    raise ValueError("; ".join(errors))

                unit_vendor = build_unit_vendor(item["unit_code"], vendor_obj["code"])
                if not unit_vendor:
                    raise ValueError(
                        f"failed to build unit_vendor from unit_code '{item['unit_code']}' "
                        f"and vendor '{vendor_obj['vendor_name']}'"
                    )

                # duplicate dalam file berdasarkan unit_vendor
                unit_vendor_l = unit_vendor.casefold()
                if unit_vendor_l in seen_unit_vendors:
                    raise ValueError(f"duplicate in file: unit_vendor '{unit_vendor}'")
                seen_unit_vendors.add(unit_vendor_l)

                prepared_items.append({
                    **item,
                    "id_category": id_category,
                    "id_vendor": vendor_obj["id"],
                    "vendor_code": vendor_obj["code"],
                    "unit_vendor": unit_vendor,
                    "unit_vendor_l": unit_vendor_l,
                    "iup_id": iup_id,
                })

                parsed_unit_vendor_keys.add(unit_vendor_l)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        if not prepared_items:
            return res

        existing_unit_vendor_rows = (
            MineUnits.objects
            .annotate(unit_vendor_l=Lower("unit_vendor"))
            .filter(unit_vendor_l__in=parsed_unit_vendor_keys)
            .values_list("unit_vendor_l", "id")
        )
        existing_unit_vendor_map = {
            unit_vendor_l: unit_id
            for unit_vendor_l, unit_id in existing_unit_vendor_rows
        }

        existing_active_assignment_unit_ids = set(
            UnitAssignment.objects
            .filter(active=True)
            .values_list("unit_id", flat=True)
        )

        # =========================================================
        # 4. BUILD OBJECTS
        # =========================================================
        to_create_units: list[MineUnits] = []
        assignment_payloads: list[dict[str, Any]] = []

        for item in prepared_items:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                if item["unit_vendor_l"] in existing_unit_vendor_map:
                    raise ValueError(
                        f"duplicate in DB: unit_vendor '{item['unit_vendor']}' already exists"
                    )

                obj = MineUnits(
                    unit_vendor=item["unit_vendor"],
                    unit_code=item["unit_code"],
                    unit_model=item["unit_model"],
                    unit_class=item["unit_class"],
                    brand=item["brand"],
                    id_category=item["id_category"],
                    id_vendor=item["id_vendor"],
                    supports=item["supports"],
                    status=item["status"],
                    description=item["description"],
                    commisioning_date=item["commisioning_date"],
                    on_hire=item["on_hire"],
                    off_hire=item["off_hire"],
                    user=user,
                )
                to_create_units.append(obj)

                if item["has_assignment_data"]:
                    assignment_payloads.append({
                        "row_no": row_no,
                        "raw": raw,
                        "unit_vendor_l": item["unit_vendor_l"],
                        "unit_vendor": item["unit_vendor"],
                        "iup_id": item["iup_id"],
                        "start_date": item["start_date"],
                        "end_date": item["end_date"],
                        "active": item["active"],
                    })

                # tandai juga sebagai existing untuk cegah duplikat antar row prepared berikutnya
                existing_unit_vendor_map[item["unit_vendor_l"]] = -1

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 5. BULK CREATE UNIT
        # =========================================================
        created_units_by_vendor: dict[str, MineUnits] = {}

        if to_create_units:
            with transaction.atomic():
                MineUnits.objects.bulk_create(to_create_units, batch_size=200)

            created_vendor_keys = [obj.unit_vendor.casefold() for obj in to_create_units]
            created_rows = (
                MineUnits.objects
                .annotate(unit_vendor_l=Lower("unit_vendor"))
                .filter(unit_vendor_l__in=created_vendor_keys)
            )

            created_units_by_vendor = {
                obj.unit_vendor.casefold(): obj
                for obj in created_rows
            }
            res.success += len(to_create_units)

        # =========================================================
        # 6. BUILD + BULK CREATE ASSIGNMENT
        # =========================================================
        to_create_assignments: list[UnitAssignment] = []

        for item in assignment_payloads:
            try:
                unit_obj = created_units_by_vendor.get(item["unit_vendor_l"])
                if not unit_obj:
                    raise ValueError(
                        f"unit '{item['unit_vendor']}' was created but cannot be resolved"
                    )

                if item["active"] and unit_obj.id in existing_active_assignment_unit_ids:
                    raise ValueError(
                        f"unit '{unit_obj.unit_vendor}' already has an active assignment in DB"
                    )

                to_create_assignments.append(
                    UnitAssignment(
                        unit=unit_obj,
                        iup_id=item["iup_id"],
                        start_date=item["start_date"],
                        end_date=item["end_date"],
                        active=item["active"],
                    )
                )

                if item["active"]:
                    existing_active_assignment_unit_ids.add(unit_obj.id)

            except Exception as e:
                res.add_error(item["row_no"], item["raw"], str(e))

        if to_create_assignments:
            with transaction.atomic():
                UnitAssignment.objects.bulk_create(to_create_assignments, batch_size=200)

        return res