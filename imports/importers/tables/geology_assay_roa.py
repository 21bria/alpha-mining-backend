from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import re

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP
from geology.models import AssayRoa
from imports.utils.parsers import (
    norm,
    parse_flexible_date,
    parse_flexible_time
)
from imports.utils.converters import to_nullable_float
from imports.utils.json_safe import json_safe_dict


def clean_code_part(value: Any) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Z0-9\-]", "", s)
    return s


def build_roa_code(iup_code: str, release_date, sample_id: str) -> str:
    iup_val = clean_code_part(iup_code or "NOIUP")
    d = release_date.strftime("%Y%m%d") if release_date else "NODATE"
    sample_val = clean_code_part(sample_id or "NOSAMPLE")
    return f"ROA-{iup_val}-{d}-{sample_val}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class AssayRoaImporter:

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        seen: set[tuple[str, str]] = set()
        parsed: list[dict[str, Any]] = []
        iup_codes_needed: set[str] = set()

        # 1. validate + collect
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = norm(row.get("iup_code")).upper()
                sample_id = norm(row.get("sample_id")).upper()
                job_number = norm(row.get("job_number")).upper()

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not sample_id:
                    raise ValueError("sample_id is required")

                file_key = (iup_code.casefold(), sample_id.casefold())
                if file_key in seen:
                    raise ValueError(
                        f"duplicate in file: iup_code '{iup_code}', sample_id '{sample_id}'"
                    )
                seen.add(file_key)

                release_date = parse_flexible_date(row.get("release_date"))
                release_time = parse_flexible_time(row.get("release_time"))

                release_roa = None
                if release_date and release_time:
                    release_roa = datetime.combine(release_date, release_time)
                elif release_date and not release_time:
                    raise ValueError("release_time is required when release_date is filled")
                elif release_time and not release_date:
                    raise ValueError("release_date is required when release_time is filled")

                code = build_roa_code(
                    iup_code=iup_code,
                    release_date=release_date,
                    sample_id=sample_id,
                )

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "code": code,
                    "iup_code": iup_code,
                    "sample_id": sample_id,
                    "job_number": job_number,
                    "release_date": release_date,
                    "release_time": release_time,
                    "release_roa": release_roa,
                    "ni": to_nullable_float(row.get("ni")),
                    "fe": to_nullable_float(row.get("fe")),
                    "al2o3": to_nullable_float(row.get("al2o3")),
                    "co": to_nullable_float(row.get("co")),
                    "mgo": to_nullable_float(row.get("mgo")),
                    "sio2": to_nullable_float(row.get("sio2")),
                    "cao": to_nullable_float(row.get("cao")),
                    "mno": to_nullable_float(row.get("mno")),
                    "cr2o3": to_nullable_float(row.get("cr2o3")),
                    "fe2o3": to_nullable_float(row.get("fe2o3")),
                    "mc": to_nullable_float(row.get("mc")),
                })

                iup_codes_needed.add(iup_code.casefold())

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # 2. resolve IUP by iup_code
        iup_map = {
            code_l: iup_id
            for code_l, iup_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }

        # 3. cek duplicate di DB berdasarkan iup_id + sample_id
        db_iup_ids_needed = list(iup_map.values())
        existing_keys: set[tuple[int, str]] = set()
        existing_codes: set[str] = set()

        if db_iup_ids_needed:
            existing_rows = (
                AssayRoa.objects
                .annotate(sample_id_l=Lower("sample_id"))
                .filter(iup_id__in=db_iup_ids_needed)
                .values_list("iup_id", "sample_id_l")
            )
            existing_keys = {(iup_id, sample_id_l) for iup_id, sample_id_l in existing_rows}

        existing_codes = set(
            AssayRoa.objects
            .annotate(code_l=Lower("code"))
            .values_list("code_l", flat=True)
        )

        # 4. build objects
        to_create: list[AssayRoa] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    raise ValueError(f"iup_code '{item['iup_code']}' not found")

                db_key = (iup_id, item["sample_id"].casefold())
                if db_key in existing_keys:
                    raise ValueError(
                        f"duplicate in DB: iup_code '{item['iup_code']}', sample_id '{item['sample_id']}' already exists"
                    )

                code_l = item["code"].casefold()
                if code_l in existing_codes:
                    raise ValueError(
                        f"duplicate in DB: code '{item['code']}' already exists"
                    )

                to_create.append(
                    AssayRoa(
                        code=item["code"],
                        iup_id=iup_id,
                        sample_id=item["sample_id"],
                        job_number=item["job_number"],
                        release_date=item["release_date"],
                        release_time=item["release_time"],
                        release_roa=item["release_roa"],
                        ni=item["ni"],
                        fe=item["fe"],
                        al2o3=item["al2o3"],
                        co=item["co"],
                        mgo=item["mgo"],
                        sio2=item["sio2"],
                        cao=item["cao"],
                        mno=item["mno"],
                        cr2o3=item["cr2o3"],
                        fe2o3=item["fe2o3"],
                        mc=item["mc"],
                        user=user,
                    )
                )

                existing_keys.add(db_key)
                existing_codes.add(code_l)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # 5. bulk create
        if to_create:
            with transaction.atomic():
                AssayRoa.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res