from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, time

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineUnits, MineIUP
from mining.models import FuelConsumption
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def normalize_unit_vendor(value: Any) -> str:
    s = norm(value).upper()
    return s.replace("_", "-").replace(" ", "-")


def build_fuel_code(iup_code: str | None = None) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    if iup_code:
        return f"{iup_code}-{ts}"
    return f"FUEL-{ts}"


def to_float_safe(value: Any) -> float:
    if value in (None, "", "-"):
        return 0.0
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return 0.0


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningFuelTransposeImporter:
    """
    rows dari generic parser, contoh:
    {
      "EXC-176-NPM": 257.24615384615475,
      "EXC-177-NPM": 333.24615384615475,
      "EXC-178-NPM": 0,
      "EXC-179-NPM": 315.24615384615475,
      "tanggal": "2025-01-02T00:00:00",
      "iup_code": "IUP-001"
    }
    """

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        seen_file: set[tuple[str, str, str]] = set()
        parsed: list[dict[str, Any]] = []
        iup_codes_needed: set[str] = set()
        unit_vendors_needed: set[str] = set()

        # =========================================================
        # 1. validate + collect
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                raw_iup = row.get("iup_code")
                raw_date = row.get("date") or row.get("tanggal")

                iup_code = norm(raw_iup).upper() if raw_iup else ""
                fuel_date = parse_flexible_date(raw_date)

                # skip row header palsu: I / II
                if not iup_code and not fuel_date:
                    non_meta_values = [
                        str(v).strip().upper()
                        for k, v in row.items()
                        if str(k).lower() not in ["iup_code", "date", "tanggal"]
                        and v not in (None, "")
                    ]
                    if non_meta_values and all(v in {"I", "II"} for v in non_meta_values):
                        res.skipped += 1
                        continue

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not fuel_date:
                    raise ValueError("date is required")

                unit_columns = [
                    col for col in row.keys()
                    if str(col).lower() not in ["iup_code", "date", "tanggal"]
                ]

                found_volume = False

                for col in unit_columns:
                    unit_vendor = normalize_unit_vendor(col)
                    volume = to_float_safe(row.get(col))

                    if not unit_vendor:
                        continue

                    if volume <= 0:
                        continue

                    found_volume = True

                    file_key = (
                        iup_code.casefold(),
                        str(fuel_date),
                        unit_vendor.casefold(),
                    )
                    if file_key in seen_file:
                        raise ValueError(
                            f"duplicate in file: iup_code '{iup_code}', date '{fuel_date}', unit_vendor '{unit_vendor}'"
                        )
                    seen_file.add(file_key)

                    parsed.append({
                        "row_no": row_no,
                        "raw": row,
                        "iup_code": iup_code,
                        "date": fuel_date,
                        "unit_vendor": unit_vendor,
                        "volume": volume,
                        "shift": "All",
                        "charging_time": time(0, 0),
                        "storage": "SOLAR",
                        "description": "Import Excel Fuel",
                    })

                    iup_codes_needed.add(iup_code.casefold())
                    unit_vendors_needed.add(unit_vendor.casefold())

                if not found_volume:
                    res.skipped += 1

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # =========================================================
        # 2. resolve master
        # =========================================================
        iup_map = {
            code_l: iup_id
            for code_l, iup_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }

        unit_map = {
            unit_vendor_l: {
                "id": unit_id,
                "unit_code": unit_code,
                "unit_vendor": unit_vendor,
            }
            for unit_vendor_l, unit_id, unit_code, unit_vendor in (
                MineUnits.objects
                .annotate(unit_vendor_l=Lower("unit_vendor"))
                .filter(unit_vendor_l__in=unit_vendors_needed)
                .values_list("unit_vendor_l", "id", "unit_code", "unit_vendor")
            )
        }

        # =========================================================
        # 3. check duplicate DB
        # =========================================================
        db_iup_ids_needed = list(iup_map.values())
        existing_keys: set[tuple[int, str, str]] = set()

        if db_iup_ids_needed:
            existing_rows = (
                FuelConsumption.objects
                .annotate(unit_l=Lower("unit"))
                .filter(iup_id__in=db_iup_ids_needed)
                .values_list("iup_id", "date", "unit_l")
            )
            existing_keys = {
                (iup_id, str(fuel_date), unit_l)
                for iup_id, fuel_date, unit_l in existing_rows
            }

        # =========================================================
        # 4. build objects
        # =========================================================
        to_create: list[FuelConsumption] = []
        fuel_field_names = {f.name for f in FuelConsumption._meta.fields}

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    raise ValueError(f"iup_code '{item['iup_code']}' not found")

                unit_obj = unit_map.get(item["unit_vendor"].casefold())
                if not unit_obj:
                    raise ValueError(f"unit_vendor '{item['unit_vendor']}' not found in master unit")

                db_key = (
                    iup_id,
                    str(item["date"]),
                    unit_obj["unit_vendor"].casefold(),
                )
                if db_key in existing_keys:
                    raise ValueError(
                        f"duplicate in DB: iup_code '{item['iup_code']}', "
                        f"date '{item['date']}', unit_vendor '{item['unit_vendor']}' already exists"
                    )

                data: dict[str, Any] = {
                    "code": build_fuel_code(item["iup_code"]),
                    "iup_id": iup_id,
                    "date": item["date"],
                    "shift": item["shift"],
                    "unit": unit_obj["unit_vendor"],  # simpan unit_vendor biar tidak ambigu
                    "drivers": None,
                    "charging_time": item["charging_time"],
                    "hours_metre": None,
                    "volume": item["volume"],
                    "storage": item["storage"],
                    "operator": None,
                    "description": item["description"],
                }

                if "unit_id" in fuel_field_names:
                    data["unit_id"] = unit_obj["id"]

                if "user" in fuel_field_names:
                    data["user"] = user

                to_create.append(FuelConsumption(**data))
                existing_keys.add(db_key)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 5. bulk create
        # =========================================================
        if to_create:
            with transaction.atomic():
                FuelConsumption.objects.bulk_create(to_create, batch_size=1000)
            res.success += len(to_create)

        return res