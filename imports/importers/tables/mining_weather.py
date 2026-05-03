from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date, datetime, time, timedelta
import re

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from mining.models import Weather
from imports.utils.parsers import norm, parse_flexible_date
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

    s = str(value).strip()
    s = s.replace(".", ":")

    formats = [
        "%H:%M",
        "%H:%M:%S",
        "%H",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue

    raise ValueError(f"time '{value}' is invalid, expected format like 09.00 or 09:00")


def calculate_duration_hours(start: time, end: time) -> float:
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)

    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    diff_seconds = (end_dt - start_dt).total_seconds()
    return round(diff_seconds / 3600, 2)


def format_time_code(value: time | None) -> str:
    if not value:
        return "NOTIME"
    return value.strftime("%H%M")


def build_weather_code(
    iup_obj,
    date_value: date,
    shift: str | None,
    category: str | None,
    start_time: time | None,
    end_time: time | None,
) -> str:
    iup_code = getattr(iup_obj, "iup_code", None) or "NOIUP"
    d = date_value.strftime("%Y%m%d") if date_value else "NODATE"
    shift_val = (shift or "NOSHIFT").strip().upper().replace(" ", "")
    category_val = (category or "NOCATEGORY").strip().upper().replace(" ", "")
    start_val = format_time_code(start_time)
    end_val = format_time_code(end_time)

    return f"WTH-{iup_code}-{d}-{shift_val}-{category_val}-{start_val}-{end_val}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningWeatherImporter:
    """
    Format import weather:

    Header contoh:
    - Iup Code
    - Date
    - Shift
    - Category
    - Start Time
    - End Time
    - Description
    """

    FIXED_COLUMNS = {
        "iup code",
        "date",
        "shift",
        "category",
        "start time",
        "end time",
        "description",
    }

    ALLOWED_CATEGORIES = {"RAINY", "SLIPPERY"}
    ALLOWED_SHIFTS = {"DAY", "NIGHT"}

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        if not rows:
            return res

        today = date.today()

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
        # 3. PARSE FILE TO WEATHER ITEMS
        # =========================================================
        parsed_items: list[dict[str, Any]] = []
        seen_keys_in_file: set[str] = set()
        weather_field_names = {f.name for f in Weather._meta.fields}

        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(get_row_value(row, "Iup Code", "iup_code"))
                date_value = parse_flexible_date(get_row_value(row, "Date", "date"))
                shift = upper_or_none(get_row_value(row, "Shift", "shift"))
                category = upper_or_none(get_row_value(row, "Category", "category"))
                start_time = parse_flexible_time(get_row_value(row, "Start Time", "start_time"))
                end_time = parse_flexible_time(get_row_value(row, "End Time", "end_time"))
                description = norm_or_none(get_row_value(row, "Description", "description"))

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not date_value:
                    raise ValueError("date is required")

                if date_value > today:
                    raise ValueError(
                        f"date '{date_value}' cannot be greater than today '{today}'"
                    )

                if not shift:
                    raise ValueError("shift is required")

                if shift not in self.ALLOWED_SHIFTS:
                    raise ValueError(
                        f"shift '{shift}' is invalid, allowed: {', '.join(sorted(self.ALLOWED_SHIFTS))}"
                    )

                if not category:
                    raise ValueError("category is required")

                if category not in self.ALLOWED_CATEGORIES:
                    raise ValueError(
                        f"category '{category}' is invalid, allowed: {', '.join(sorted(self.ALLOWED_CATEGORIES))}"
                    )

                if not start_time:
                    raise ValueError("start_time is required")

                if not end_time:
                    raise ValueError("end_time is required")

                iup_obj = iup_objs.get(iup_code.casefold())
                if not iup_obj:
                    raise ValueError(f"iup_code '{iup_code}' not found")

                duration = calculate_duration_hours(start_time, end_time)

                unique_key = (
                    f"{iup_obj.id}|{date_value}|{shift}|{category}|"
                    f"{start_time.strftime('%H:%M:%S')}|{end_time.strftime('%H:%M:%S')}"
                )

                if unique_key in seen_keys_in_file:
                    raise ValueError(
                        f"duplicate in file for iup '{iup_code}', date '{date_value}', "
                        f"shift '{shift}', category '{category}', "
                        f"time '{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}'"
                    )

                seen_keys_in_file.add(unique_key)

                code = build_weather_code(
                    iup_obj=iup_obj,
                    date_value=date_value,
                    shift=shift,
                    category=category,
                    start_time=start_time,
                    end_time=end_time,
                )

                item = {
                    "row_no": row_no,
                    "raw": row,
                    "iup_id": iup_obj.id,
                    "iup_obj": iup_obj,
                    "date": date_value,
                    "shift": shift.title(),
                    "category": category.title(),
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "description": description,
                    "code": code,
                }

                if "user" in weather_field_names:
                    item["user"] = user

                if "task_id" in weather_field_names:
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
        dates_needed = {item["date"] for item in parsed_items}
        shifts_needed = {item["shift"] for item in parsed_items}
        categories_needed = {item["category"] for item in parsed_items}
        start_times_needed = {item["start_time"] for item in parsed_items}
        end_times_needed = {item["end_time"] for item in parsed_items}

        existing_keys = {
            (
                f"{obj['iup_id']}|{obj['date']}|{obj['shift']}|{obj['category']}|"
                f"{obj['start_time'].strftime('%H:%M:%S')}|{obj['end_time'].strftime('%H:%M:%S')}"
            )
            for obj in Weather.objects.filter(
                iup_id__in=iup_ids_needed,
                date__in=dates_needed,
                shift__in=shifts_needed,
                category__in=categories_needed,
                start_time__in=start_times_needed,
                end_time__in=end_times_needed,
            ).values("iup_id", "date", "shift", "category", "start_time", "end_time")
        }

        # =========================================================
        # 5. BUILD OBJECTS
        # =========================================================
        to_create: list[Weather] = []

        for item in parsed_items:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                unique_key = (
                    f"{item['iup_id']}|{item['date']}|{item['shift']}|{item['category']}|"
                    f"{item['start_time'].strftime('%H:%M:%S')}|{item['end_time'].strftime('%H:%M:%S')}"
                )

                if unique_key in existing_keys:
                    raise ValueError(
                        f"duplicate in DB for "
                        f"iup '{item['iup_obj'].iup_code}', "
                        f"date '{item['date']}', "
                        f"shift '{item['shift']}', "
                        f"category '{item['category']}', "
                        f"time '{item['start_time'].strftime('%H:%M')}-{item['end_time'].strftime('%H:%M')}'"
                    )

                data = {
                    "iup_id": item["iup_id"],
                    "date": item["date"],
                    "shift": item["shift"],
                    "category": item["category"],
                    "start_time": item["start_time"],
                    "end_time": item["end_time"],
                    "duration": item["duration"],
                    "description": item["description"],
                    "code": item["code"],
                }

                if "user" in item:
                    data["user"] = item["user"]

                if "task_id" in item:
                    data["task_id"] = item["task_id"]

                to_create.append(Weather(**data))
                existing_keys.add(unique_key)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 6. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                Weather.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res