from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from django.db.models.functions import Lower

from master.models import SellingCode, MineIUP


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, row, msg))


def norm(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


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


def to_nullable_int(value: Any) -> int | None:
    if value is None:
        return None

    s = str(value).strip()
    if s == "":
        return None

    try:
        return int(float(s))
    except ValueError:
        raise ValueError(f"invalid integer '{value}'")


class SellingCodeImporter:
    ALLOWED_TYPES = {"LIS", "SAS"}

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        seen: set[tuple[str, str]] = set()
        parsed: list[dict[str, Any]] = []
        iup_codes_needed: set[str] = set()

        # 1. validate + collect
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = norm(row.get("iup_code")).upper()
                code = norm(row.get("code")).upper()
                type_value = norm(row.get("type")).upper()

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not code:
                    raise ValueError("code is required")

                if not type_value:
                    raise ValueError("type is required")

                if type_value not in self.ALLOWED_TYPES:
                    raise ValueError("type must be LIS or SAS")

                file_key = (iup_code.casefold(), code.casefold())
                if file_key in seen:
                    raise ValueError(
                        f"duplicate in file: iup_code '{iup_code}', code '{code}'"
                    )
                seen.add(file_key)

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "code": code,
                    "type": type_value,
                    "description": to_nullable_str(row.get("description")),
                    "truck_factors": to_nullable_float(row.get("truck_factors")),
                    "sublot_close": to_nullable_str(row.get("sublot_close")),
                    "group_close": to_nullable_int(row.get("group_close")),
                    "ritase_max": to_nullable_int(row.get("ritase_max")),
                    "tonnage": to_nullable_float(row.get("tonnage")),
                    "ni": to_nullable_float(row.get("ni")),
                    "fe": to_nullable_float(row.get("fe")),
                    "mgo": to_nullable_float(row.get("mgo")),
                    "sio2": to_nullable_float(row.get("sio2")),
                })

                iup_codes_needed.add(iup_code.casefold())

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # 2. resolve IUP by iup_code
        iup_map = {
            code_l: iup_id
            for code_l, iup_id in MineIUP.objects.annotate(code_l=Lower("iup_code"))
            .filter(code_l__in=iup_codes_needed)
            .values_list("code_l", "id")
        }

        # 3. existing keys in DB
        db_iup_ids_needed = list(iup_map.values())

        existing_keys = set()
        if db_iup_ids_needed:
            existing_rows = (
                SellingCode.objects.annotate(code_l=Lower("code"))
                .filter(iup_id__in=db_iup_ids_needed)
                .values_list("iup_id", "code_l")
            )
            existing_keys = {(iup_id, code_l) for iup_id, code_l in existing_rows}

        # 4. build objects
        to_create: list[SellingCode] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    raise ValueError(f"iup_code '{item['iup_code']}' not found")

                db_key = (iup_id, item["code"].casefold())
                if db_key in existing_keys:
                    raise ValueError(
                        f"Duplicate : iup_code '{item['iup_code']}', code '{item['code']}' already exists"
                    )

                to_create.append(
                    SellingCode(
                        iup_id=iup_id,
                        code=item["code"],
                        type=item["type"],
                        description=item["description"],
                        truck_factors=item["truck_factors"],
                        sublot_close=item["sublot_close"],
                        group_close=item["group_close"],
                        ritase_max=item["ritase_max"],
                        tonnage=item["tonnage"],
                        ni=item["ni"],
                        fe=item["fe"],
                        mgo=item["mgo"],
                        sio2=item["sio2"],
                        active=1,
                        user=user
                    )
                )

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # 5. bulk create
        if to_create:
            with transaction.atomic():
                SellingCode.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res