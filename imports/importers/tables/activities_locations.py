from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from mining.models import MiningActivityLocation
from imports.utils.parsers import norm
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
    normalized = {
        normalize_header(k): v
        for k, v in row.items()
    }
    for candidate in candidates:
        val = normalized.get(normalize_header(candidate))
        if val not in (None, ""):
            return val
    return None


def clean_code_part(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    return s


def build_activity_location_code(iup_obj, name: str | None) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    iup_part = clean_code_part(iup_code)
    name_part = clean_code_part(name or "NONAME")
    return f"{iup_part}{name_part}"

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


class ActivitiesLocationsImporter:
    """
    Format import mining activity locations:

    Header contoh:
    - Iup Code
    - Name
    - Description
    """

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        if not rows:
            return res

        # =========================================================
        # 1. COLLECT IUP CODE
        # =========================================================
        iup_codes_needed: set[str] = set()

        for row in rows:
            iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
            if iup_code:
                iup_codes_needed.add(iup_code.casefold())

        # =========================================================
        # 2. RESOLVE IUP OBJECTS
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
        # 3. PARSE FILE
        # =========================================================
        parsed_items: list[dict[str, Any]] = []
        seen_keys_in_file: set[str] = set()
        seen_codes_in_file: set[str] = set()

        location_field_names = {f.name for f in MiningActivityLocation._meta.fields}

        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
                name = norm_or_none(get_row_value(row, "Name", "name"))
                description = norm_or_none(get_row_value(row, "Description", "description"))

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not name:
                    raise ValueError("name is required")

                iup_obj = iup_objs.get(iup_code.casefold())
                if not iup_obj:
                    raise ValueError(f"iup_code '{iup_code}' not found")

                # unique per iup + name
                unique_key = f"{iup_obj.id}|{name.casefold()}"

                if unique_key in seen_keys_in_file:
                    raise ValueError(
                        f"duplicate in file for iup '{iup_code}' and name '{name}'"
                    )

                code = build_activity_location_code(iup_obj=iup_obj, name=name)

                if code in seen_codes_in_file:
                    raise ValueError(
                        f"duplicate code in file '{code}' generated from name '{name}'"
                    )

                seen_keys_in_file.add(unique_key)
                seen_codes_in_file.add(code)

                item = {
                    "row_no": row_no,
                    "raw": row,
                    "iup_id": iup_obj.id,
                    "iup_obj": iup_obj,
                    "name": name,
                    "description": description,
                    "code": code,
                }

                if "user" in location_field_names:
                    item["user"] = user

                if "task_id" in location_field_names:
                    item["task_id"] = task_id

                parsed_items.append(item)

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed_items:
            return res

        # =========================================================
        # 4. CHECK DUPLICATE IN DB
        # =========================================================
        iup_ids_needed = {item["iup_id"] for item in parsed_items}
        names_needed = {item["name"] for item in parsed_items}
        codes_needed = {item["code"] for item in parsed_items}

        existing_name_keys = {
            f"{obj['iup_id']}|{obj['name'].casefold()}"
            for obj in MiningActivityLocation.objects.filter(
                iup_id__in=iup_ids_needed,
                name__in=names_needed,
            ).values("iup_id", "name")
        }

        existing_codes = set()
        if "code" in location_field_names:
            existing_codes = set(
                MiningActivityLocation.objects.filter(
                    code__in=codes_needed
                ).values_list("code", flat=True)
            )

        # =========================================================
        # 5. BUILD OBJECTS
        # =========================================================
        to_create: list[MiningActivityLocation] = []

        for item in parsed_items:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                unique_key = f"{item['iup_id']}|{item['name'].casefold()}"

                if unique_key in existing_name_keys:
                    res.add_skip(
                        row_no,
                        raw,
                        f"skipped duplicate in DB for iup '{item['iup_obj'].iup_code}' and name '{item['name']}'",
                    )
                    continue

                if "code" in location_field_names and item["code"] in existing_codes:
                    res.add_skip(
                        row_no,
                        raw,
                        f"skipped duplicate code in DB '{item['code']}'",
                    )
                    continue

                data = {
                    "iup_id": item["iup_id"],
                    "name": item["name"],
                    "description": item["description"],
                }

                if "code" in location_field_names:
                    data["code"] = item["code"]

                if "user" in item:
                    data["user"] = item["user"]

                if "task_id" in item:
                    data["task_id"] = item["task_id"]

                to_create.append(MiningActivityLocation(**data))
                existing_name_keys.add(unique_key)

                if "code" in location_field_names:
                    existing_codes.add(item["code"])

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 6. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                MiningActivityLocation.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res