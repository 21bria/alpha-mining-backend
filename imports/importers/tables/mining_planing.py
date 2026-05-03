from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from mining.models import planProductions
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.converters import to_nullable_float
from imports.utils.json_safe import json_safe_dict


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
    sources: str | None,
    vendors: str | None,
) -> str:
    d = date_plan.strftime("%Y%m%d")

    parts = [
        "PLAN",
        clean_code_part(iup_code),
        d,
        clean_code_part(category),
        clean_code_part(sources),
        clean_code_part(vendors),
    ]

    # buang part kosong
    return "-".join([p for p in parts if p])


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningPlanningImporter:
    """
    Import planning mining / plan productions

    Kolom contoh:
    - iup_code / IUP Code
    - date_plan / Date Plan
    - category / Category
    - sources / Sources
    - vendors / Vendors
    - topsoil / Top Soil
    - ob / OB
    - lim / LIM
    - sap / SAP
    - waste / Waste
    - quarry / Quarry
    - ballast / Ballast
    - biomass / Biomass
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
                sources = norm_or_none(row.get("sources") or row.get("Sources"))
                vendors = norm_or_none(row.get("vendors") or row.get("Vendors"))

                topsoil = to_nullable_float(row.get("topsoil") or row.get("Top Soil"))
                ob = to_nullable_float(row.get("ob") or row.get("OB"))
                lim = to_nullable_float(row.get("lim") or row.get("LIM"))
                sap = to_nullable_float(row.get("sap") or row.get("SAP"))
                waste = to_nullable_float(row.get("waste") or row.get("Waste"))
                quarry = to_nullable_float(row.get("quarry") or row.get("Quarry"))
                ballast = to_nullable_float(row.get("ballast") or row.get("Ballast"))
                biomass = to_nullable_float(row.get("biomass") or row.get("Biomass"))

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not date_plan:
                    raise ValueError("date_plan is required")

                if date_plan > today:
                    raise ValueError(
                        f"date_plan '{date_plan}' cannot be greater than today '{today}'"
                    )

                # default numerik ke 0
                topsoil = 0 if topsoil is None else topsoil
                ob = 0 if ob is None else ob
                lim = 0 if lim is None else lim
                sap = 0 if sap is None else sap
                waste = 0 if waste is None else waste
                quarry = 0 if quarry is None else quarry
                ballast = 0 if ballast is None else ballast
                biomass = 0 if biomass is None else biomass

                code = build_plan_code(
                    iup_code=iup_code,
                    date_plan=date_plan,
                    category=category,
                    sources=sources,
                    vendors=vendors,
                )

                code_l = code.casefold()
                if code_l in seen_codes:
                    raise ValueError(f"duplicate in file: code '{code}'")
                seen_codes.add(code_l)

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "date_plan": date_plan,
                    "category": category,
                    "sources": sources,
                    "vendors": vendors,
                    "topsoil": topsoil,
                    "ob": ob,
                    "lim": lim,
                    "sap": sap,
                    "waste": waste,
                    "quarry": quarry,
                    "ballast": ballast,
                    "biomass": biomass,
                    "code": code,
                })

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
            planProductions.objects
            .annotate(code_l=Lower("code"))
            .filter(code_l__in=codes_needed)
            .values_list("code_l", flat=True)
        )

        # =========================================================
        # 4. BUILD OBJECTS
        # =========================================================
        to_create: list[planProductions] = []
        plan_field_names = {f.name for f in planProductions._meta.fields}

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
                    "sources": item["sources"],
                    "vendors": item["vendors"],
                    "topsoil": item["topsoil"],
                    "ob": item["ob"],
                    "lim": item["lim"],
                    "sap": item["sap"],
                    "waste": item["waste"],
                    "quarry": item["quarry"],
                    "ballast": item["ballast"],
                    "biomass": item["biomass"],
                }

                if "user" in plan_field_names:
                    data["user"] = user

                if "task_id" in plan_field_names:
                    data["task_id"] = task_id

                to_create.append(planProductions(**data))
                existing_codes.add(code_l)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 5. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                planProductions.objects.bulk_create(to_create, batch_size=200)
            res.success += len(to_create)

        return res