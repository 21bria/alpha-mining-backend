from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from mining.models import PlanProduction, PlanProductionDetail
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.converters import to_nullable_float
from imports.utils.json_safe import json_safe_dict


MATERIAL_COLUMNS = {
    "Top Soil": ["topsoil", "Top Soil", "TOP SOIL"],
    "OB": ["ob", "OB"],
    "LIM": ["lim", "LIM"],
    "SAP": ["sap", "SAP"],
    "WMS": ["wms","Wms","WMS"],
    "Waste": ["waste", "Waste", "WASTE"],
    "Quarry": ["quarry", "Quarry", "QUARRY"],
    "Ballast": ["ballast", "Ballast", "BALLAST"],
    "Biomass": ["biomass", "Biomass", "BIOMASS"],
    "Spoil": ["spoil", "Spoil", "SPOIL"],
}


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def clean_code_part(value: str | None) -> str:
    if not value:
        return ""

    return (
        str(value)
        .strip()
        .upper()
        .replace(" ", "")
        .replace("/", "-")
        .replace("_", "-")
    )


def build_plan_code(
    iup_code: str,
    date_plan: date,
    category: str | None,
    source_code: str | None,
    vendor_code: str | None,
) -> str:
    d = date_plan.strftime("%Y%m%d")

    parts = [
        "PLAN",
        clean_code_part(iup_code),
        d,
        clean_code_part(category),
        clean_code_part(source_code),
        clean_code_part(vendor_code),
    ]

    return "-".join([p for p in parts if p])


def get_first_value(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row:
            return row.get(key)
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


class MiningPlanProductionImporter:
    """
    Import planning mining / plan productions.

    Template lama tetap support:
    - iup_code / IUP Code
    - date_plan / Date Plan
    - category / Category
    - sources / Sources
    - vendors / Vendors
    - Top Soil
    - OB
    - LIM
    - SAP
    - Waste
    - Quarry
    - Ballast
    - Biomass
    """

    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()

        seen_codes: set[str] = set()
        parsed: list[dict[str, Any]] = []
        iup_codes_needed: set[str] = set()

        today = date.today()

        # =========================================================
        # 1. VALIDATE + COLLECT
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(row.get("iup_code") or row.get("IUP Code"))
                date_plan = parse_flexible_date(
                    row.get("date_plan") or row.get("Date Plan")
                )

                category = norm_or_none(row.get("category") or row.get("Category"))
                source_code = norm_or_none(
                    row.get("source_code")
                    or row.get("sources")
                    or row.get("Sources")
                )
                vendor_code = norm_or_none(
                    row.get("vendor_code")
                    or row.get("vendors")
                    or row.get("Vendors")
                )

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not date_plan:
                    raise ValueError("date_plan is required")

                # if date_plan > today:
                #     raise ValueError(
                #         f"date_plan '{date_plan}' cannot be greater than today '{today}'"
                #     )

                details: list[dict[str, Any]] = []

                for material_name, keys in MATERIAL_COLUMNS.items():
                    raw_value = get_first_value(row, keys)
                    tonnage = to_nullable_float(raw_value)
                    tonnage = 0 if tonnage is None else tonnage

                    if tonnage > 0:
                        details.append(
                            {
                                "material_code": material_name,
                                "material_name": material_name,
                                "tonnage": tonnage,
                            }
                        )

                if not details:
                    raise ValueError("at least one material tonnage must be greater than 0")

                code = build_plan_code(
                    iup_code=iup_code,
                    date_plan=date_plan,
                    category=category,
                    source_code=source_code,
                    vendor_code=vendor_code,
                )

                code_l = code.casefold()

                if code_l in seen_codes:
                    raise ValueError(f"duplicate in file: code '{code}'")

                seen_codes.add(code_l)

                parsed.append(
                    {
                        "row_no": row_no,
                        "raw": row,
                        "iup_code": iup_code,
                        "date_plan": date_plan,
                        "category": category,
                        "source_code": source_code,
                        "vendor_code": vendor_code,
                        "details": details,
                        "code": code,
                    }
                )

                iup_codes_needed.add(iup_code.casefold())

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # =========================================================
        # 2. RESOLVE IUP
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

        # =========================================================
        # 3. CHECK DUPLICATE DI DB BERDASARKAN CODE
        # =========================================================
        codes_needed = {item["code"].casefold() for item in parsed}

        existing_codes = set(
            PlanProduction.objects
            .annotate(code_l=Lower("code"))
            .filter(code_l__in=codes_needed)
            .values_list("code_l", flat=True)
        )

        # =========================================================
        # 4. BUILD OBJECTS
        # =========================================================
        plans_to_create: list[PlanProduction] = []
        details_by_code: dict[str, list[dict[str, Any]]] = {}

        plan_field_names = {f.name for f in PlanProduction._meta.fields}

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                iup_id = iup_map.get(item["iup_code"].casefold())

                if not iup_id:
                    raise ValueError(f"iup_code '{item['iup_code']}' not found")

                code_l = item["code"].casefold()

                if code_l in existing_codes:
                    raise ValueError(
                        f"duplicate in DB: code '{item['code']}' already exists"
                    )

                data: dict[str, Any] = {
                    "iup_id": iup_id,
                    "code": item["code"],
                    "date_plan": item["date_plan"],
                    "category": item["category"],
                    "source_code": item["source_code"],
                    "vendor_code": item["vendor_code"],
                }

                if "user" in plan_field_names:
                    data["user"] = user

                if "task_id" in plan_field_names:
                    data["task_id"] = task_id

                plan = PlanProduction(**data)

                plans_to_create.append(plan)
                details_by_code[item["code"]] = item["details"]

                existing_codes.add(code_l)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 5. BULK CREATE HEADER + DETAILS
        # =========================================================
        if plans_to_create:
            with transaction.atomic():
                created_plans = PlanProduction.objects.bulk_create(
                    plans_to_create,
                    batch_size=200,
                )

                detail_objects: list[PlanProductionDetail] = []

                for plan in created_plans:
                    for detail in details_by_code.get(plan.code, []):
                        detail_objects.append(
                            PlanProductionDetail(
                                plan=plan,
                                material_code=detail["material_code"],
                                material_name=detail["material_name"],
                                tonnage=detail["tonnage"],
                            )
                        )

                if detail_objects:
                    PlanProductionDetail.objects.bulk_create(
                        detail_objects,
                        batch_size=500,
                    )

            res.success += len(plans_to_create)

        return res