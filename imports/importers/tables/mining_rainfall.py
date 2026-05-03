from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date
import re

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from mining.models import RainfallPoint, Rainfall
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.converters import to_nullable_float
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def display_header(value: str) -> str:
    return str(value).replace("_", " ").strip().title()


def normalize_header(value: Any) -> str:
    s = str(value or "").strip().casefold()
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_point_name(value: Any) -> str:
    return normalize_header(value)


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


def build_rainfall_code(iup_obj, date_value: date, point_obj) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    d = date_value.strftime("%Y%m%d") if date_value else "NODATE"

    point_name = getattr(point_obj, "name", "") or "NOPOINT"
    point_val = point_name.strip().upper().replace(" ", "")

    return f"RF-{iup_code}-{d}-{point_val}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningRainfallImporter:
    """
    Format import rainfall:

    Header contoh:
    - Iup Code
    - Date
    - Jetty
    - View Point
    - Camp
    - Pit A

    Semua kolom selain fixed columns dianggap sebagai RainfallPoint.
    """

    FIXED_COLUMNS = {"iup code", "date"}

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        if not rows:
            return res

        today = date.today()

        # =========================================================
        # 1. COLLECT IUP CODE & POINT HEADERS
        # =========================================================
        iup_codes_needed: set[str] = set()
        point_names_needed: set[str] = set()

        for row in rows:
            iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
            if iup_code:
                iup_codes_needed.add(iup_code.casefold())

            for raw_key in row.keys():
                key_norm = normalize_header(raw_key)
                if not key_norm:
                    continue
                if key_norm in self.FIXED_COLUMNS:
                    continue
                point_names_needed.add(key_norm)

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
        # 3. RESOLVE RAINFALL POINT OBJECTS
        # =========================================================
        point_objs: dict[str, RainfallPoint] = {}
        for obj in RainfallPoint.objects.all():
            key = normalize_point_name(obj.name)
            if key in point_names_needed:
                point_objs[key] = obj

        # =========================================================
        # 4. PARSE FILE TO RAINFALL ITEMS
        # =========================================================
        parsed_items: list[dict[str, Any]] = []
        seen_keys_in_file: set[str] = set()
        rainfall_field_names = {f.name for f in Rainfall._meta.fields}

        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
                date_value = parse_flexible_date(get_row_value(row, "Date", "date"))

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not date_value:
                    raise ValueError("date is required")

                if date_value > today:
                    raise ValueError(
                        f"date '{date_value}' cannot be greater than today '{today}'"
                    )

                iup_obj = iup_objs.get(iup_code.casefold())
                if not iup_obj:
                    raise ValueError(f"iup_code '{iup_code}' not found")

                found_valid_point = False
                unknown_headers: list[str] = []

                for raw_key, raw_value in row.items():
                    key_norm = normalize_header(raw_key)
                    if not key_norm:
                        continue

                    if key_norm in self.FIXED_COLUMNS:
                        continue

                    point_obj = point_objs.get(key_norm)
                    if not point_obj:
                        unknown_headers.append(str(raw_key))
                        continue

                    milimeter = to_nullable_float(raw_value)

                    # skip kalau kosong
                    if milimeter is None:
                        continue

                    # kalau 0 mau ikut skip, buka ini:
                    # if milimeter is None or milimeter == 0:
                    #     continue

                    found_valid_point = True

                    unique_key = f"{iup_obj.id}|{date_value}|{point_obj.id}"
                    if unique_key in seen_keys_in_file:
                        raise ValueError(
                            f"duplicate in file for iup '{iup_code}', date '{date_value}', point '{point_obj.name}'"
                        )

                    seen_keys_in_file.add(unique_key)

                    code = build_rainfall_code(
                        iup_obj=iup_obj,
                        date_value=date_value,
                        point_obj=point_obj,
                    )

                    item = {
                        "row_no": row_no,
                        "raw": row,
                        "iup_id": iup_obj.id,
                        "iup_obj": iup_obj,
                        "date": date_value,
                        "point_id": point_obj.id,
                        "point_obj": point_obj,
                        "milimeter": milimeter,
                        "code": code,
                    }

                    if "user" in rainfall_field_names:
                        item["user"] = user

                    if "task_id" in rainfall_field_names:
                        item["task_id"] = task_id

                    parsed_items.append(item)

                if unknown_headers:
                    raise ValueError(
                        "rainfall point header not found in master: "
                        + ", ".join(display_header(h) for h in unknown_headers)
                    )

                if not found_valid_point:
                    res.skipped += 1

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed_items:
            return res

        # =========================================================
        # 5. CHECK DUPLICATE IN DB
        # =========================================================
        iup_ids_needed = {item["iup_id"] for item in parsed_items}
        dates_needed = {item["date"] for item in parsed_items}
        point_ids_needed = {item["point_id"] for item in parsed_items}

        existing_keys = {
            f"{obj['iup_id']}|{obj['date']}|{obj['point_id']}"
            for obj in Rainfall.objects.filter(
                iup_id__in=iup_ids_needed,
                date__in=dates_needed,
                point_id__in=point_ids_needed,
            ).values("iup_id", "date", "point_id")
        }

        # =========================================================
        # 6. BUILD OBJECTS
        # =========================================================
        to_create: list[Rainfall] = []

        for item in parsed_items:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                unique_key = f"{item['iup_id']}|{item['date']}|{item['point_id']}"
                if unique_key in existing_keys:
                    raise ValueError(
                        f"duplicate in DB for iup/date/point: "
                        f"'{item['iup_obj'].iup_code}' / '{item['date']}' / '{item['point_obj'].name}'"
                    )

                data = {
                    "iup_id": item["iup_id"],
                    "date": item["date"],
                    "point_id": item["point_id"],
                    "milimeter": item["milimeter"],
                    "code": item["code"],
                }

                if "user" in item:
                    data["user"] = item["user"]

                if "task_id" in item:
                    data["task_id"] = item["task_id"]

                to_create.append(Rainfall(**data))
                existing_keys.add(unique_key)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 7. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                Rainfall.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res