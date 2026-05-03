from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

from django.db import transaction
from django.db.models.functions import Lower

from mining.models import MiningActivity, MiningActivityCategories
from imports.utils.parsers import norm
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


def normalize_category(value: Any) -> str:
    s = str(value or "").strip().upper()
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


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningActivityImporter:
    """
    Format import mining activity:

    Header contoh:
    - Activity Code
    - Activity Name
    - Activity Category
    """

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        if not rows:
            return res

        activity_codes_needed: set[str] = set()
        activity_names_needed: set[str] = set()
        category_values_needed: set[str] = set()

        # =========================================================
        # 1. COLLECT DATA YANG DIBUTUHKAN
        # =========================================================
        for row in rows:
            activity_code = upper_or_none(
                get_row_value(row, "activity_code", "Activity Code")
            )
            activity_name = norm_or_none(
                get_row_value(row, "activity_name", "Activity Name")
            )
            activity_category = normalize_category(
                get_row_value(row, "activity_category", "Activity Category")
            )

            if activity_code:
                activity_codes_needed.add(activity_code.casefold())

            if activity_name:
                activity_names_needed.add(activity_name.casefold())

            if activity_category:
                category_values_needed.add(activity_category)

        # =========================================================
        # 2. RESOLVE CATEGORY
        #    prioritas: category, fallback: name
        # =========================================================
        all_categories = list(MiningActivityCategories.objects.all())

        category_map: dict[str, MiningActivityCategories] = {}

        for obj in all_categories:
            if obj.category:
                category_map[normalize_category(obj.category)] = obj
            if obj.name:
                category_map[normalize_category(obj.name)] = obj

        # =========================================================
        # 3. CHECK EXISTING DATA DI DB
        # =========================================================
        existing_codes = set(
            MiningActivity.objects
            .annotate(code_l=Lower("code"))
            .filter(code_l__in=activity_codes_needed)
            .values_list("code_l", flat=True)
        )

        existing_names = set(
            MiningActivity.objects
            .annotate(name_l=Lower("name"))
            .filter(name_l__in=activity_names_needed)
            .values_list("name_l", flat=True)
        )

        # =========================================================
        # 4. PARSE & VALIDATE ROW
        # =========================================================
        parsed_items: list[dict[str, Any]] = []
        seen_codes_in_file: set[str] = set()
        seen_names_in_file: set[str] = set()

        activity_field_names = {f.name for f in MiningActivity._meta.fields}

        for row_no, row in enumerate(rows, start=1):
            try:
                activity_code = upper_or_none(
                    get_row_value(row, "activity_code", "Activity Code")
                )
                activity_name = norm_or_none(
                    get_row_value(row, "activity_name", "Activity Name")
                )
                activity_category = normalize_category(
                    get_row_value(row, "activity_category", "Activity Category")
                )

                if not activity_code:
                    raise ValueError("activity_code is required")

                if not activity_name:
                    raise ValueError("activity_name is required")

                if not activity_category:
                    raise ValueError("activity_category is required")

                code_l = activity_code.casefold()
                name_l = activity_name.casefold()

                if code_l in seen_codes_in_file:
                    raise ValueError(f"duplicate in file: activity_code '{activity_code}'")

                if name_l in seen_names_in_file:
                    raise ValueError(f"duplicate in file: activity_name '{activity_name}'")

                if code_l in existing_codes:
                    raise ValueError(f"duplicate in DB: activity_code '{activity_code}' already exists")

                if name_l in existing_names:
                    raise ValueError(f"duplicate in DB: activity_name '{activity_name}' already exists")

                category_obj = category_map.get(activity_category)
                if not category_obj:
                    raise ValueError(
                        f"activity_category '{activity_category}' not found in MiningActivityCategories.category"
                    )

                seen_codes_in_file.add(code_l)
                seen_names_in_file.add(name_l)

                item = {
                    "row_no": row_no,
                    "raw": row,
                    "code": activity_code,
                    "name": activity_name,
                    "status_id": category_obj.id,
                }

                if "user" in activity_field_names:
                    item["user"] = user

                if "task_id" in activity_field_names:
                    item["task_id"] = task_id

                parsed_items.append(item)

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed_items:
            return res

        # =========================================================
        # 5. BUILD OBJECTS
        # =========================================================
        to_create: list[MiningActivity] = []

        for item in parsed_items:
            data = {
                "code": item["code"],
                "name": item["name"],
                "status_id": item["status_id"],
            }

            if "user" in item:
                data["user"] = item["user"]

            if "task_id" in item:
                data["task_id"] = item["task_id"]

            to_create.append(MiningActivity(**data))

        # =========================================================
        # 6. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                MiningActivity.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res