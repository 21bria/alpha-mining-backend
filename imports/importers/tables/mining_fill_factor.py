from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP, Material
from mining.models import mineAdditionFactor

from imports.utils.parsers import norm
from imports.utils.converters import to_nullable_float
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def normalize_header(value: Any) -> str:
    s = str(value or "").strip().casefold()
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def get_row_value(row: dict[str, Any], *candidates: str) -> Any:
    normalized = {normalize_header(k): v for k, v in row.items()}
    for candidate in candidates:
        val = normalized.get(normalize_header(candidate))
        if val not in (None, ""):
            return val
    return None


def clean_code_part(value: Any) -> str:
    s = str(value or "").strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Za-z0-9\-]", "", s)
    return s


def build_fill_factor_code(iup_obj, type_unit: str | None, material_name: str | None) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    iup_part = clean_code_part(iup_code)
    unit_part = clean_code_part(type_unit or "NOUNIT")
    material_part = clean_code_part(material_name or "NOMATERIAL")
    return f"{iup_part}{unit_part}{material_part}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))

    def add_skip(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.skipped += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningFillFactorImporter:
    """
    Header contoh:
    - iup_code
    - type_unit
    - material
    - density_bcm
    - density_lcm
    - bucket_capacity
    - validation
    - description
    """

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        if not rows:
            return res

        # =========================================================
        # 1. COLLECT IUP + MATERIAL
        # =========================================================
        iup_codes_needed: set[str] = set()
        material_names_needed: set[str] = set()

        for row in rows:
            iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
            material_name = norm_or_none(get_row_value(row, "Material", "material"))

            if iup_code:
                iup_codes_needed.add(iup_code.casefold())

            if material_name:
                material_names_needed.add(material_name.casefold())

        # =========================================================
        # 2. RESOLVE IUP
        # =========================================================
        iup_objs = {
            obj.code_l: obj
            for obj in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
            )
        }

        # =========================================================
        # 3. RESOLVE MATERIAL BY NAME
        # =========================================================
        material_name_map: dict[str, str] = {}

        material_objs = (
            Material.objects
            .annotate(name_l=Lower("name"))
            .filter(name_l__in=material_names_needed)
            .values("name", "name_l")
        )

        for obj in material_objs:
            material_name_map[obj["name_l"]] = obj["name"]

        # =========================================================
        # 4. PARSE ROWS
        # =========================================================
        parsed_items: list[dict[str, Any]] = []
        seen_keys_in_file: set[str] = set()
        fill_factor_field_names = {f.name for f in mineAdditionFactor._meta.fields}

        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
                type_unit = norm_or_none(get_row_value(row, "Type Unit", "type_unit"))
                material_input = norm_or_none(get_row_value(row, "Material", "material"))
                density_bcm = to_nullable_float(get_row_value(row, "Density BCM", "density_bcm"))
                density_lcm = to_nullable_float(get_row_value(row, "Density LCM", "density_lcm"))
                bucket_capacity = to_nullable_float(get_row_value(row, "Bucket Capacity", "bucket_capacity"))
                validation = norm_or_none(get_row_value(row, "Validation", "validation"))
                description = norm_or_none(get_row_value(row, "Description", "description"))

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not type_unit:
                    raise ValueError("type_unit is required")

                if not material_input:
                    raise ValueError("material is required")

                iup_obj = iup_objs.get(iup_code.casefold())
                if not iup_obj:
                    raise ValueError(f"iup_code '{iup_code}' not found")

                material_name = material_name_map.get(material_input.casefold())
                if not material_name:
                    raise ValueError(f"material '{material_input}' not found in master material")

                unique_key = (
                    f"{iup_obj.id}|"
                    f"{type_unit.casefold()}|"
                    f"{material_name.casefold()}"
                )

                if unique_key in seen_keys_in_file:
                    raise ValueError(
                        f"duplicate in file for iup '{iup_code}', "
                        f"type_unit '{type_unit}', material '{material_name}'"
                    )

                seen_keys_in_file.add(unique_key)

                code = build_fill_factor_code(
                    iup_obj=iup_obj,
                    type_unit=type_unit,
                    material_name=material_name,
                )

                item = {
                    "row_no": row_no,
                    "raw": row,
                    "iup_id": iup_obj.id,
                    "iup_obj": iup_obj,
                    "type_unit": type_unit,
                    "material": material_name,
                    "density_bcm": density_bcm,
                    "density_lcm": density_lcm,
                    "bucket_capacity": bucket_capacity,
                    "validation": validation,
                    "description": description,
                    "code": code,
                }

                if "user" in fill_factor_field_names:
                    item["user"] = user

                if "task_id" in fill_factor_field_names:
                    item["task_id"] = task_id

                parsed_items.append(item)

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed_items:
            return res

        # =========================================================
        # 5. CHECK DUPLICATE IN DB
        # =========================================================
        iup_ids_needed = {item["iup_id"] for item in parsed_items}
        type_units_needed = {item["type_unit"] for item in parsed_items}
        materials_needed = {item["material"] for item in parsed_items}

        existing_keys = {
            f"{obj['iup_id']}|{obj['type_unit'].casefold()}|{obj['material'].casefold()}"
            for obj in mineAdditionFactor.objects.filter(
                iup_id__in=iup_ids_needed,
                type_unit__in=type_units_needed,
                material__in=materials_needed,
            ).values("iup_id", "type_unit", "material")
        }

        # =========================================================
        # 6. BUILD OBJECTS
        # =========================================================
        to_create: list[mineAdditionFactor] = []

        for item in parsed_items:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                unique_key = (
                    f"{item['iup_id']}|"
                    f"{item['type_unit'].casefold()}|"
                    f"{item['material'].casefold()}"
                )

                if unique_key in existing_keys:
                    res.add_skip(
                        row_no,
                        raw,
                        f"skipped duplicate in DB for iup '{item['iup_obj'].iup_code}', "
                        f"type_unit '{item['type_unit']}', material '{item['material']}'"
                    )
                    continue

                data = {
                    "iup_id": item["iup_id"],
                    "type_unit": item["type_unit"],
                    "material": item["material"],
                    "density_bcm": item["density_bcm"],
                    "density_lcm": item["density_lcm"],
                    "bucket_capacity": item["bucket_capacity"],
                    "validation": item["validation"],
                    "description": item["description"],
                    "code": item["code"],
                }

                if "user" in item:
                    data["user"] = item["user"]

                if "task_id" in item:
                    data["task_id"] = item["task_id"]

                to_create.append(mineAdditionFactor(**data))
                existing_keys.add(unique_key)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 7. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                mineAdditionFactor.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res