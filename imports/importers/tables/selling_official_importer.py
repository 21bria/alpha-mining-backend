from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Max
from django.db.models.functions import Lower

from master.models import MineIUP, StockFactories, SellingSurveyor
from selling.models import SellingOfficial


def make_json_safe(value: Any):
    if isinstance(value, dict):
        return {k: make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [make_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [make_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, make_json_safe(row), msg))


def norm(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def clean_code_part(value: Any) -> str:
    s = norm(value).upper()
    return s.replace(" ", "").replace("/", "-")


def to_nullable_str(value: Any) -> str | None:
    s = norm(value)
    return s or None


def to_nullable_float(value: Any) -> float | None:
    if value is None:
        return None

    s = str(value).strip()
    if s == "":
        return None

    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"invalid number '{value}'")


def to_nullable_date(value: Any):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    s = str(value).strip()
    if s == "":
        return None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"invalid date '{value}'")


def resolve_fk_by_name(model, field: str, values: set[str]) -> dict[str, int]:
    cleaned_values = {norm(v).casefold() for v in values if norm(v)}
    if not cleaned_values:
        return {}

    qs = (
        model.objects
        .annotate(field_l=Lower(field))
        .filter(field_l__in=cleaned_values)
        .values_list("field_l", "id")
    )
    return {key: obj_id for key, obj_id in qs}


def build_selling_official_code(
    iup_code: str,
    type_selling: str,
    product_code: str,
    re_assay: int,
) -> str:
    iup_part = clean_code_part(iup_code)
    type_part = clean_code_part(type_selling)
    product_part = clean_code_part(product_code)
    return f"{iup_part}-{type_part}-{product_part}-R{re_assay}"


class SellingOfficialImporter:
    ALLOWED_TYPES = {"LIS", "SAS"}

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        parsed: list[dict[str, Any]] = []
        iup_codes_needed: set[str] = set()
        factory_names_needed: set[str] = set()
        surveyor_names_needed: set[str] = set()

        # duplicate dalam file: (iup_code, type_selling, product_code) -> urutan
        file_group_counter: dict[tuple[str, str, str], int] = defaultdict(int)

        # 1. validate + collect
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = norm(row.get("iup_code")).upper()
                type_selling = norm(row.get("type_selling")).upper()
                product_code = norm(row.get("product_code")).upper()
                factory_stock = norm(row.get("factory_stock"))
                name_surveyor = norm(row.get("name_surveyor"))

                errors = []

                if not iup_code:
                    errors.append("iup_code is required")

                if not type_selling:
                    errors.append("type_selling is required")
                elif type_selling not in self.ALLOWED_TYPES:
                    errors.append("type_selling must be LIS or SAS")

                if not product_code:
                    errors.append("product_code is required")

                if not name_surveyor:
                    errors.append("name_surveyor is required")

                if errors:
                    raise ValueError("; ".join(errors))

                base_key = (
                    iup_code.casefold(),
                    type_selling.casefold(),
                    product_code.casefold(),
                )

                file_seq = file_group_counter[base_key]
                file_group_counter[base_key] += 1

                parsed.append({
                    "row_no": row_no,
                    "raw": make_json_safe(row),
                    "iup_code": iup_code,
                    "factory_stock": factory_stock or None,
                    "name_surveyor": name_surveyor or None,
                    "type_selling": type_selling,
                    "tonnage": to_nullable_float(row.get("tonnage")),
                    "so_number": to_nullable_str(row.get("so_number")),
                    "product_code": product_code,
                    "barge_code": to_nullable_str(row.get("barge_code")),
                    "ni": to_nullable_float(row.get("ni")),
                    "co": to_nullable_float(row.get("co")),
                    "al2o3": to_nullable_float(row.get("al2o3")),
                    "cao": to_nullable_float(row.get("cao")),
                    "cr2o3": to_nullable_float(row.get("cr2o3")),
                    "fe": to_nullable_float(row.get("fe")),
                    "mgo": to_nullable_float(row.get("mgo")),
                    "sio2": to_nullable_float(row.get("sio2")),
                    "mno": to_nullable_float(row.get("mno")),
                    "mc": to_nullable_float(row.get("mc")),
                    "start_date": to_nullable_date(row.get("start_date")),
                    "end_date": to_nullable_date(row.get("end_date")),
                    "description": to_nullable_str(row.get("description")),
                    "file_seq": file_seq,
                })

                iup_codes_needed.add(iup_code)

                if factory_stock:
                    factory_names_needed.add(factory_stock)

                if name_surveyor:
                    surveyor_names_needed.add(name_surveyor)

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # 2. resolve FK by name/code
        iup_map = resolve_fk_by_name(MineIUP, "iup_code", iup_codes_needed)
        factory_map = resolve_fk_by_name(StockFactories, "factory_stock", factory_names_needed)
        surveyor_map = resolve_fk_by_name(SellingSurveyor, "name_surveyor", surveyor_names_needed)

        # 3. ambil max re_assay dari DB per grup
        db_iup_ids_needed = list(iup_map.values())
        existing_max_map: dict[tuple[int, str, str], int] = {}

        if db_iup_ids_needed:
            existing_rows = (
                SellingOfficial.objects
                .annotate(
                    type_l=Lower("type_selling"),
                    product_l=Lower("product_code"),
                )
                .filter(iup_id__in=db_iup_ids_needed)
                .values("iup_id", "type_l", "product_l")
                .annotate(max_re_assay=Max("re_assay"))
            )

            existing_max_map = {
                (
                    row["iup_id"],
                    (row["type_l"] or "").casefold(),
                    (row["product_l"] or "").casefold(),
                ): int(row["max_re_assay"])
                for row in existing_rows
                if row["max_re_assay"] is not None
            }

        # counter per grup dalam proses build
        assigned_counter: dict[tuple[int, str, str], int] = defaultdict(int)

        # 4. build objects
        to_create: list[SellingOfficial] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                errors = []

                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    errors.append(f"iup_code '{item['iup_code']}' not found")

                factory_id = None
                if item["factory_stock"]:
                    factory_id = factory_map.get(item["factory_stock"].casefold())
                    if not factory_id:
                        errors.append(f"factory_stock '{item['factory_stock']}' not found")

                surveyor_id = None
                if item["name_surveyor"]:
                    surveyor_id = surveyor_map.get(item["name_surveyor"].casefold())
                    if not surveyor_id:
                        errors.append(f"name_surveyor '{item['name_surveyor']}' not found")

                if errors:
                    raise ValueError("; ".join(errors))

                base_db_key = (
                    iup_id,
                    item["type_selling"].casefold(),
                    item["product_code"].casefold(),
                )

                db_max = existing_max_map.get(base_db_key, -1)
                local_offset = assigned_counter[base_db_key]
                next_re_assay = db_max + 1 + local_offset
                assigned_counter[base_db_key] += 1

                code = build_selling_official_code(
                    iup_code=item["iup_code"],
                    type_selling=item["type_selling"],
                    product_code=item["product_code"],
                    re_assay=next_re_assay,
                )

                to_create.append(
                    SellingOfficial(
                        code=code,
                        iup_id=iup_id,
                        type_selling=item["type_selling"],
                        tonnage=item["tonnage"],
                        id_factory=factory_id,
                        surveyor_id=surveyor_id,
                        so_number=item["so_number"],
                        product_code=item["product_code"],
                        barge_code=item["barge_code"],
                        ni=item["ni"],
                        co=item["co"],
                        al2o3=item["al2o3"],
                        cao=item["cao"],
                        cr2o3=item["cr2o3"],
                        fe=item["fe"],
                        mgo=item["mgo"],
                        sio2=item["sio2"],
                        mno=item["mno"],
                        mc=item["mc"],
                        start_date=item["start_date"],
                        end_date=item["end_date"],
                        description=item["description"],
                        re_assay=next_re_assay,
                        user=user,
                    )
                )

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        if not to_create:
            return res

        # 5. bulk create
        try:
            with transaction.atomic():
                SellingOfficial.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)
        except Exception as e:
            # kalau bulk gagal total, catat per batch umum
            for item in parsed:
                res.add_error(item["row_no"], item["raw"], f"bulk_create failed: {str(e)}")

        return res