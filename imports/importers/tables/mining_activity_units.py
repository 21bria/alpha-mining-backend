from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import re

from django.db import transaction
from django.db.models.functions import Lower

from master.models import (
    MineIUP,
    MineUnits,
    MiningActivityCategories,
    MiningActivity,
    MiningActivityLocation,
)
from mining.models import HmUnit, HmUnitDetail
from imports.utils.parsers import norm, parse_flexible_date
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


def normalize_name(value: Any) -> str:
    s = str(value or "").strip().casefold()
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


def parse_flexible_time(value: Any) -> time | None:
    if value in (None, ""):
        return None

    if isinstance(value, time):
        return value

    s = str(value).strip()
    s = s.replace(".", ":")

    for fmt in ("%H:%M:%S", "%H:%M", "%H"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue

    raise ValueError(
        f"time '{value}' is invalid, expected format like 06.00, 06:00, or 06:00:00"
    )


def parse_duration_minutes(value: Any) -> int | None:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float, Decimal)):
        return int(round(float(value) * 60))

    s = str(value).strip()
    s = s.replace(".", ":")

    for fmt in ("%H:%M:%S", "%H:%M", "%H"):
        try:
            t = datetime.strptime(s, fmt).time()
            return (t.hour * 60) + t.minute
        except ValueError:
            continue

    raise ValueError(
        f"duration '{value}' is invalid, expected format like 12.00.00 or 12:00:00"
    )


def calculate_duration_minutes(start: time, end: time) -> int:
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)

    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    diff_seconds = (end_dt - start_dt).total_seconds()
    return int(diff_seconds // 60)


def clean_code(value: str | None, default: str) -> str:
    if not value:
        return default
    return str(value).strip().upper().replace(" ", "")


def format_time_code(value: time | None, default: str) -> str:
    if not value:
        return default
    return value.strftime("%H%M")


def build_hm_unit_code(
    iup_obj,
    unit_obj,
    date_value: date | None,
    shift: str | None,
) -> str:
    """
    Contoh:
    HMU-IUP-001-KOBEXINDO-20260317-DAY
    """
    iup_code = clean_code(getattr(iup_obj, "iup_code", None), "NOIUP")
    unit_vendor = clean_code(getattr(unit_obj, "unit_vendor", None), "NOUNIT")
    date_val = date_value.strftime("%Y%m%d") if date_value else "NODATE"
    shift_val = clean_code(shift, "NOSHIFT")

    return f"HMU-{iup_code}-{unit_vendor}-{date_val}-{shift_val}"


def build_hm_detail_code(
    iup_obj,
    unit_obj,
    date_value: date | None,
    shift: str | None,
    start_time: time | None,
    end_time: time | None,
) -> str:
    """
    Contoh:
    HMD-IUP-001-KOBEXINDO-20260317-DAY-0600-1800
    """
    iup_code = clean_code(getattr(iup_obj, "iup_code", None), "NOIUP")
    unit_vendor = clean_code(getattr(unit_obj, "unit_vendor", None), "NOUNIT")
    date_val = date_value.strftime("%Y%m%d") if date_value else "NODATE"
    shift_val = clean_code(shift, "NOSHIFT")
    start_val = format_time_code(start_time, "NOSTART")
    end_val = format_time_code(end_time, "NOEND")

    return f"HMD-{iup_code}-{unit_vendor}-{date_val}-{shift_val}-{start_val}-{end_val}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningActivityUnitsImporter:
    """
    Format import HM Unit Detail

    Header contoh:
    - Iup Code
    - Date
    - Shift
    - Unit Code        -> dipakai untuk cari ke field master.unit_vendor
    - Start Time
    - End Time
    - Duration
    - Activity
    - Status
    - Location
    - Category
    - Description
    """

    ALLOWED_SHIFTS = {"DAY", "NIGHT"}
    ALLOWED_CATEGORIES = {"MINING", "PROJECT"}

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        if not rows:
            return res

        # =========================================================
        # 1. COLLECT KEYS
        # =========================================================
        iup_codes_needed: set[str] = set()
        unit_codes_needed: set[str] = set()

        for row in rows:
            iup_code = upper_or_none(get_row_value(row, "iup_code", "Iup Code"))
            unit_code = upper_or_none(get_row_value(row, "unit_code", "Unit Code"))

            if iup_code:
                iup_codes_needed.add(iup_code.casefold())

            if unit_code:
                unit_codes_needed.add(unit_code.casefold())

        # =========================================================
        # 2. MASTER MAPS
        # =========================================================
        iup_map = {
            obj.code_l: obj
            for obj in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
            )
        }

        # sesuai arahan: cari dari unit_vendor
        unit_map = {
            obj.code_l: obj
            for obj in (
                MineUnits.objects
                .annotate(code_l=Lower("unit_vendor"))
                .filter(code_l__in=unit_codes_needed)
            )
        }

        status_map = {
            normalize_name(obj.name): obj
            for obj in MiningActivityCategories.objects.all()
        }

        location_map = {
            normalize_name(obj.name): obj
            for obj in MiningActivityLocation.objects.all()
        }

        activity_map = {
            (normalize_name(obj.name), obj.status_id): obj
            for obj in MiningActivity.objects.select_related("status").all()
        }

        # =========================================================
        # 3. PRELOAD EXISTING PARENT
        # =========================================================
        existing_hm_units = {
            (obj.iup_id, obj.unit_id, obj.date, obj.shift): obj
            for obj in HmUnit.objects.all()
        }

        hm_unit_field_names = {f.name for f in HmUnit._meta.fields}
        detail_field_names = {f.name for f in HmUnitDetail._meta.fields}

        hm_has_code = "code" in hm_unit_field_names
        detail_has_code = "code" in detail_field_names

        parsed_rows: list[dict[str, Any]] = []
        seen_detail_keys_in_file: set[str] = set()

        # =========================================================
        # 4. PARSE & VALIDATE ROWS
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(get_row_value(row, "iup_code", "Iup Code"))
                date_value = parse_flexible_date(get_row_value(row, "date", "Date"))
                shift_raw = upper_or_none(get_row_value(row, "shift", "Shift"))
                unit_code = upper_or_none(get_row_value(row, "unit_code", "Unit Code"))

                start_time = parse_flexible_time(get_row_value(row, "start_time", "Start Time"))
                end_time = parse_flexible_time(get_row_value(row, "end_time", "End Time"))
                duration_file = parse_duration_minutes(get_row_value(row, "duration", "Duration"))

                activity_name_raw = norm_or_none(get_row_value(row, "activity", "Activity"))
                status_name_raw = norm_or_none(get_row_value(row, "status", "Status"))
                location_name_raw = norm_or_none(get_row_value(row, "location", "Location"))
                category_raw = upper_or_none(get_row_value(row, "category", "Category"))
                description = norm_or_none(
                    get_row_value(row, "description", "Description", "remark", "Remark")
                )

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not date_value:
                    raise ValueError("date is required")

                if not shift_raw:
                    raise ValueError("shift is required")

                if shift_raw not in self.ALLOWED_SHIFTS:
                    raise ValueError(
                        f"shift '{shift_raw}' is invalid, allowed: {', '.join(sorted(self.ALLOWED_SHIFTS))}"
                    )

                if not unit_code:
                    raise ValueError("unit_code is required")

                if not start_time:
                    raise ValueError("start_time is required")

                if not end_time:
                    raise ValueError("end_time is required")

                if not activity_name_raw:
                    raise ValueError("activity is required")

                if not status_name_raw:
                    raise ValueError("status is required")

                if not location_name_raw:
                    raise ValueError("location is required")

                if category_raw and category_raw not in self.ALLOWED_CATEGORIES:
                    raise ValueError(
                        f"category '{category_raw}' is invalid, allowed: {', '.join(sorted(self.ALLOWED_CATEGORIES))}"
                    )

                iup_obj = iup_map.get(iup_code.casefold())
                if not iup_obj:
                    raise ValueError(f"iup_code '{iup_code}' not found")

                unit_obj = unit_map.get(unit_code.casefold())
                if not unit_obj:
                    raise ValueError(f"unit_code/vendor '{unit_code}' not found")

                status_obj = status_map.get(normalize_name(status_name_raw))
                if not status_obj:
                    raise ValueError(f"status '{status_name_raw}' not found")

                activity_obj = activity_map.get(
                    (normalize_name(activity_name_raw), status_obj.id)
                )
                if not activity_obj:
                    raise ValueError(
                        f"activity '{activity_name_raw}' not found or not matched with status '{status_obj.name}'"
                    )

                location_obj = location_map.get(normalize_name(location_name_raw))
                if not location_obj:
                    raise ValueError(f"location '{location_name_raw}' not found")

                duration_calc = calculate_duration_minutes(start_time, end_time)
                if duration_calc <= 0:
                    raise ValueError("duration is invalid")

                if duration_file is not None and duration_file != duration_calc:
                    raise ValueError(
                        f"duration mismatch: file '{duration_file}' minutes, calculated '{duration_calc}' minutes"
                    )

                shift_val = shift_raw.title()  # Day / Night
                hm_key = (iup_obj.id, unit_obj.id, date_value, shift_val)

                detail_key_file = (
                    f"{iup_obj.id}|{unit_obj.id}|{date_value}|{shift_val}|"
                    f"{start_time.strftime('%H:%M:%S')}|{end_time.strftime('%H:%M:%S')}"
                )

                if detail_key_file in seen_detail_keys_in_file:
                    raise ValueError(
                        f"duplicate in file for unit/vendor '{unit_code}', date '{date_value}', "
                        f"shift '{shift_val}', time '{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}'"
                    )
                seen_detail_keys_in_file.add(detail_key_file)

                hm_code = build_hm_unit_code(
                    iup_obj=iup_obj,
                    unit_obj=unit_obj,
                    date_value=date_value,
                    shift=shift_val,
                )

                detail_code = build_hm_detail_code(
                    iup_obj=iup_obj,
                    unit_obj=unit_obj,
                    date_value=date_value,
                    shift=shift_val,
                    start_time=start_time,
                    end_time=end_time,
                )

                parsed = {
                    "row_no": row_no,
                    "raw": row,
                    "hm_key": hm_key,
                    "iup_obj": iup_obj,
                    "unit_obj": unit_obj,
                    "date": date_value,
                    "shift": shift_val,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_min": duration_calc,
                    "status_obj": status_obj,
                    "activity_obj": activity_obj,
                    "location_obj": location_obj,
                    "category": category_raw.title() if category_raw else None,
                    "description": description,
                    "hm_code": hm_code,
                    "detail_code": detail_code,
                }

                if "user" in hm_unit_field_names or "user" in detail_field_names:
                    parsed["user"] = user

                if "task_id" in hm_unit_field_names or "task_id" in detail_field_names:
                    parsed["task_id"] = task_id

                parsed_rows.append(parsed)

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed_rows:
            return res

        # =========================================================
        # 5. PRELOAD EXISTING CODES
        # =========================================================
        existing_hm_codes = set()
        if hm_has_code:
            hm_codes_needed = [item["hm_code"].casefold() for item in parsed_rows]
            existing_hm_codes = set(
                HmUnit.objects
                .annotate(code_l=Lower("code"))
                .filter(code_l__in=hm_codes_needed)
                .values_list("code_l", flat=True)
            )

        existing_detail_codes = set()
        if detail_has_code:
            detail_codes_needed = [item["detail_code"].casefold() for item in parsed_rows]
            existing_detail_codes = set(
                HmUnitDetail.objects
                .annotate(code_l=Lower("code"))
                .filter(code_l__in=detail_codes_needed)
                .values_list("code_l", flat=True)
            )

        # =========================================================
        # 6. PREPARE PARENT CREATE
        # =========================================================
        hm_units_to_create: list[HmUnit] = []
        seen_new_hm_codes: set[str] = set()

        valid_rows: list[dict[str, Any]] = []

        for item in parsed_rows:
            row_no = item["row_no"]
            raw = item["raw"]
            hm_key = item["hm_key"]

            try:
                if hm_key in existing_hm_units:
                    valid_rows.append(item)
                    continue

                hm_code_l = item["hm_code"].casefold()

                if hm_has_code:
                    if hm_code_l in existing_hm_codes:
                        raise ValueError(
                            f"duplicate in DB: hm_unit code '{item['hm_code']}' already exists"
                        )
                    if hm_code_l in seen_new_hm_codes:
                        raise ValueError(
                            f"duplicate in file: hm_unit code '{item['hm_code']}' already exists"
                        )

                data = {
                    "iup_id": item["iup_obj"].id,
                    "unit_id": item["unit_obj"].id,
                    "date": item["date"],
                    "shift": item["shift"],
                    "hm_start": Decimal("0.00"),
                    "hm_end": Decimal("0.00"),
                    "status": "DRAFT",
                }

                if hm_has_code:
                    data["code"] = item["hm_code"]

                if "user" in hm_unit_field_names:
                    data["user"] = item.get("user")

                if "task_id" in hm_unit_field_names:
                    data["task_id"] = item.get("task_id")

                hm_obj = HmUnit(**data)
                hm_units_to_create.append(hm_obj)
                existing_hm_units[hm_key] = hm_obj

                if hm_has_code:
                    seen_new_hm_codes.add(hm_code_l)

                valid_rows.append(item)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        if not valid_rows:
            return res

        # =========================================================
        # 7. SAVE PARENT + RELOAD
        # =========================================================
        with transaction.atomic():
            if hm_units_to_create:
                HmUnit.objects.bulk_create(hm_units_to_create, batch_size=500)

            hm_keys_needed = {item["hm_key"] for item in valid_rows}
            existing_hm_units = {
                (obj.iup_id, obj.unit_id, obj.date, obj.shift): obj
                for obj in HmUnit.objects.filter(
                    iup_id__in={k[0] for k in hm_keys_needed},
                    unit_id__in={k[1] for k in hm_keys_needed},
                    date__in={k[2] for k in hm_keys_needed},
                    shift__in={k[3] for k in hm_keys_needed},
                )
            }

            # =====================================================
            # 8. CHECK EXISTING DETAIL DB
            # =====================================================
            hm_unit_ids_needed = {
                existing_hm_units[item["hm_key"]].id
                for item in valid_rows
                if item["hm_key"] in existing_hm_units
            }

            existing_detail_keys = {
                (
                    f"{obj['hm_unit_id']}|"
                    f"{obj['start_time'].strftime('%H:%M:%S')}|"
                    f"{obj['end_time'].strftime('%H:%M:%S')}"
                )
                for obj in HmUnitDetail.objects.filter(
                    hm_unit_id__in=hm_unit_ids_needed
                ).values("hm_unit_id", "start_time", "end_time")
            }

            # =====================================================
            # 9. BUILD DETAIL OBJECTS
            # =====================================================
            details_to_create: list[HmUnitDetail] = []
            seen_new_detail_codes: set[str] = set()

            for item in valid_rows:
                row_no = item["row_no"]
                raw = item["raw"]

                try:
                    hm_unit_obj = existing_hm_units.get(item["hm_key"])
                    if not hm_unit_obj:
                        raise ValueError("hm_unit parent not found after create")

                    detail_key_db = (
                        f"{hm_unit_obj.id}|"
                        f"{item['start_time'].strftime('%H:%M:%S')}|"
                        f"{item['end_time'].strftime('%H:%M:%S')}"
                    )

                    if detail_key_db in existing_detail_keys:
                        raise ValueError(
                            f"duplicate in DB for unit/vendor '{getattr(item['unit_obj'], 'unit_vendor', None)}', "
                            f"date '{item['date']}', shift '{item['shift']}', "
                            f"time '{item['start_time'].strftime('%H:%M')}-{item['end_time'].strftime('%H:%M')}'"
                        )

                    detail_code_l = item["detail_code"].casefold()
                    if detail_has_code:
                        if detail_code_l in existing_detail_codes:
                            raise ValueError(
                                f"duplicate in DB: code '{item['detail_code']}' already exists"
                            )
                        if detail_code_l in seen_new_detail_codes:
                            raise ValueError(
                                f"duplicate in file: code '{item['detail_code']}' already exists"
                            )

                    data = {
                        "iup_id": item["iup_obj"].id,
                        "hm_unit_id": hm_unit_obj.id,
                        "start_time": item["start_time"],
                        "end_time": item["end_time"],
                        "duration_min": item["duration_min"],
                        "status_id": item["status_obj"].id,
                        "activity_id": item["activity_obj"].id,
                        "location_id": item["location_obj"].id,
                        "category": item["category"],
                        "description": item["description"] or "",
                    }

                    if detail_has_code:
                        data["code"] = item["detail_code"]

                    if "user" in detail_field_names:
                        data["user"] = item.get("user")

                    if "task_id" in detail_field_names:
                        data["task_id"] = item.get("task_id")

                    details_to_create.append(HmUnitDetail(**data))
                    existing_detail_keys.add(detail_key_db)

                    if detail_has_code:
                        seen_new_detail_codes.add(detail_code_l)

                except Exception as e:
                    res.add_error(row_no, raw, str(e))

            # =====================================================
            # 10. BULK CREATE DETAILS
            # =====================================================
            if details_to_create:
                HmUnitDetail.objects.bulk_create(details_to_create, batch_size=1000)
                res.success += len(details_to_create)

        return res