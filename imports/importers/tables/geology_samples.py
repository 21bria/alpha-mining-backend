from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from datetime import date
from django.db.models import Q
from django.db import transaction
from django.db.models.functions import Lower
from core.models.base import make_code
from master.models import (
    MineIUP,
    Material,
    SourceMinesDumping,
    SourceMinesDome,
    SampleMethod,
    SampleType,
)
from geology.models import SampleProductions

from imports.utils.parsers import (
    norm,
    parse_flexible_date,
)
from imports.utils.converters import (
    to_nullable_float,
    to_nullable_int,
)
from imports.utils.json_safe import json_safe_dict

from master.services.sample_type import (
    get_production_geology_sample_type_map,
    build_pattern,
)

def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None

def build_sample_code(iup_code: str, sample_number: str) -> str:
    return make_code(iup_code, sample_number)

@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))

class SamplesImporter:
    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        seen_sample: set[tuple[str, str]] = set()
        seen_kode_batch: set[tuple[Any, str]] = set()

        parsed: list[dict[str, Any]] = []

        iup_codes_needed: set[str] = set()
        material_names_needed: set[str] = set()
        area_names_needed: set[str] = set()
        point_names_needed: set[str] = set()
        method_names_needed: set[str] = set()
        type_names_needed: set[str] = set()

        today = date.today()
        sample_type_map = get_production_geology_sample_type_map()

        # 1. VALIDATE + COLLECT
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = norm(row.get("iup_code")).upper()
                shift = upper_or_none(row.get("shift"))
                tgl_sample = parse_flexible_date(row.get("date_sample"))
                sample_type_name = upper_or_none(row.get("sample_type"))
                sample_method_name = norm_or_none(row.get("sampling_method"))
                material_name = norm_or_none(row.get("material"))
                sampling_area_name = norm_or_none(row.get("sampling_area"))
                sampling_point_name = norm_or_none(row.get("sampling_point"))

                required_fields = {
                    "iup_code": iup_code,
                    "shift": shift,
                    "date_sample": tgl_sample,
                    "sample_type": sample_type_name,
                    "sampling_method": sample_method_name,
                    "material": material_name,
                    "sampling_area": sampling_area_name,
                    "sampling_point": sampling_point_name,
                }

                missing_fields = [
                    field for field, value in required_fields.items() if not value
                ]

                if missing_fields:
                    raise ValueError(
                        "required fields missing: " + ", ".join(missing_fields)
                    )
                
                if tgl_sample > today:
                    raise ValueError(
                        f"date_sample '{tgl_sample}' cannot be greater than today '{today}'"
                    )
                            
                            
                from_rl = norm_or_none(row.get("from"))
                to_rl = norm_or_none(row.get("to"))
                batch_code = norm_or_none(row.get("batch"))
                increments = to_nullable_int(row.get("increments"))
                fraction = norm_or_none(row.get("fraction"))
                size = norm_or_none(row.get("size"))
                sample_weight = to_nullable_float(row.get("sample_weight"))
                sample_number = norm(row.get("sample_id")).upper()
                remark = norm_or_none(row.get("remark"))
                primer_raw = to_nullable_float(row.get("primer_raw"))
                duplicate_raw = to_nullable_float(row.get("duplicat_raw"))
                sampling_deskripsi = norm_or_none(row.get("sampling_desc"))

                if not sample_number:
                    raise ValueError("sample_id is required")

                # duplicate dalam file berdasarkan iup_code + sample_number
                file_key = (iup_code.casefold(), sample_number.casefold())
                if file_key in seen_sample:
                    raise ValueError(
                        f"duplicate in file: iup_code '{iup_code}', sample_id '{sample_number}'"
                    )
                seen_sample.add(file_key)

                if increments is None:
                    increments = 0

                # ambil sample_dup dari DUP_
                sample_dup = None
                if sampling_deskripsi:
                    desc = sampling_deskripsi.strip()
                    if desc.startswith("DUP_"):
                        sample_dup = desc.replace("DUP_", "", 1)

                # ambil truck dari sampling method
                truck = None
                if sample_method_name:
                    truck = re.sub(r"^(TS_|GRB_)", "", sample_method_name)

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "tgl_sample": tgl_sample,
                    "shift": shift,
                    "sample_type_name": sample_type_name,
                    "sample_method_name": sample_method_name,
                    "material_name": material_name,
                    "sampling_area_name": sampling_area_name,
                    "sampling_point_name": sampling_point_name,
                    "from_rl": from_rl,
                    "to_rl": to_rl,
                    "batch_code": batch_code,
                    "increments": increments,
                    "fraction": fraction,
                    "size": size,
                    "sample_weight": sample_weight,
                    "sample_number": sample_number,
                    "remark": remark,
                    "primer_raw": primer_raw,
                    "duplicate_raw": duplicate_raw,
                    "sampling_deskripsi": sampling_deskripsi,
                    "sample_dup": sample_dup,
                    "truck": truck,
                })

                iup_codes_needed.add(iup_code.casefold())

                if material_name:
                    material_names_needed.add(material_name.casefold())
                if sampling_area_name:
                    area_names_needed.add(sampling_area_name.casefold())
                if sampling_point_name:
                    point_names_needed.add(sampling_point_name.casefold())
                if sample_method_name:
                    method_names_needed.add(sample_method_name.casefold())
                if sample_type_name:
                    type_names_needed.add(sample_type_name.casefold())

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # 2. RESOLVE MASTER DATA
        iup_map = {
            code_l: iup_id
            for code_l, iup_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }

        material_map = {
            name_l: obj_id
            for name_l, obj_id in (
                Material.objects
                .annotate(name_l=Lower("name"))
                .filter(name_l__in=material_names_needed)
                .values_list("name_l", "id")
            )
        }

        area_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SourceMinesDumping.objects
                .annotate(name_l=Lower("dumping_point"))
                .filter(name_l__in=area_names_needed)
                .values_list("name_l", "id")
            )
        }

        point_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SourceMinesDome.objects
                .annotate(name_l=Lower("pile_id"))
                .filter(name_l__in=point_names_needed)
                .values_list("name_l", "id")
            )
        }

        method_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SampleMethod.objects
                .annotate(name_l=Lower("sample_method"))
                .filter(name_l__in=method_names_needed)
                .values_list("name_l", "id")
            )
        }

        type_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SampleType.objects
                .annotate(name_l=Lower("type_sample"))
                .filter(
                    Q(is_production=True) | Q(is_geology=True),
                    name_l__in=type_names_needed,
                    status=1,
                )
                .values_list("name_l", "id")
            )
        }

        # 3. EXISTING CHECK
        db_iup_ids_needed = list(iup_map.values())

        existing_sample_keys: set[tuple[Any, str]] = set()
        existing_batch_keys: set[tuple[Any, str]] = set()
        existing_codes: set[str] = set()

        if db_iup_ids_needed:
            existing_rows = (
                SampleProductions.objects
                .annotate(sample_number_l=Lower("sample_number"))
                .filter(iup_id__in=db_iup_ids_needed)
                .values_list("iup_id", "sample_number_l")
            )
            existing_sample_keys = {
                (iup_id, sample_number_l)
                for iup_id, sample_number_l in existing_rows
            }

            existing_batch_rows = (
                SampleProductions.objects
                .annotate(kode_batch_l=Lower("kode_batch"))
                .filter(iup_id__in=db_iup_ids_needed)
                .exclude(kode_batch__isnull=True)
                .exclude(kode_batch="")
                .values_list("iup_id", "kode_batch_l")
            )
            existing_batch_keys = {
                (iup_id, kode_batch_l)
                for iup_id, kode_batch_l in existing_batch_rows
            }

            existing_codes = set(
                SampleProductions.objects
                .filter(iup_id__in=db_iup_ids_needed)
                .exclude(code__isnull=True)
                .exclude(code="")
                .values_list("code", flat=True)
            )

        # 4. BUILD OBJECTS
        to_create: list[SampleProductions] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                errors = []

                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    raise ValueError(f"iup_code '{item['iup_code']}' not found")

                sample_type_name = item["sample_type_name"]
                sample_method_name = item["sample_method_name"]
                material_name = item["material_name"]
                sampling_area_name = item["sampling_area_name"]
                sampling_point_name = item["sampling_point_name"]

                id_type_sample = type_map.get(sample_type_name.casefold()) if sample_type_name else None
                id_method = method_map.get(sample_method_name.casefold()) if sample_method_name else None
                id_material = material_map.get(material_name.casefold()) if material_name else None
                sampling_area = area_map.get(sampling_area_name.casefold()) if sampling_area_name else None
                sampling_point = point_map.get(sampling_point_name.casefold()) if sampling_point_name else None

                if sample_type_name and id_type_sample is None:
                    errors.append(f"sample_type '{sample_type_name}' not found")
                if sample_method_name and id_method is None:
                    errors.append(f"sampling_method '{sample_method_name}' not found")
                if material_name and id_material is None:
                    errors.append(f"material '{material_name}' not found")
                if sampling_area_name and sampling_area is None:
                    errors.append(f"sampling_area '{sampling_area_name}' not found")
                if sampling_point_name and sampling_point is None:
                    errors.append(f"sampling_point '{sampling_point_name}' not found")

                if errors:
                    raise ValueError("; ".join(errors))

                db_key = (iup_id, item["sample_number"].casefold())
                if db_key in existing_sample_keys:
                    raise ValueError(
                        f"duplicate in DB: iup_code '{item['iup_code']}', "
                        f"sample_number '{item['sample_number']}' already exists"
                    )

                code = build_sample_code(item["iup_code"], item["sample_number"])
                if code in existing_codes:
                    raise ValueError(f"duplicate code in DB: '{code}' already exists")

                sample_type_final = (sample_type_name or "").strip().upper() or None
                kode_batch = None

                sample_type_cfg = sample_type_map.get(sample_type_final)

                if not sample_type_cfg:
                    raise ValueError(
                        f"sample_type '{sample_type_final}' is not active for production/geology"
                    )

                pattern = sample_type_cfg.get("batch_pattern")

                kode_batch = build_pattern(
                    pattern,
                    type=sample_type_final,
                    material=str(id_material or ""),
                    truck=item["truck"] or "",
                    point=str(sampling_point or ""),
                    pit_dome=str(sample_number or ""),
                    batch=item["batch_code"] or "",
                )

                if kode_batch:
                    batch_key = (iup_id, kode_batch.casefold())

                    if batch_key in existing_batch_keys:
                        raise ValueError(
                            f"duplicate {sample_type_final} kode_batch in DB: "
                            f"iup_code '{item['iup_code']}', kode_batch '{kode_batch}' already exists"
                        )

                    if batch_key in seen_kode_batch:
                        raise ValueError(
                            f"duplicate {sample_type_final} kode_batch in file: "
                            f"iup_code '{item['iup_code']}', kode_batch '{kode_batch}'"
                        )

                    seen_kode_batch.add(batch_key)

                obj = SampleProductions(
                    iup_id=iup_id,
                    code=code,
                    tgl_sample=item["tgl_sample"],
                    shift=item["shift"],
                    id_type_sample=id_type_sample,
                    id_method=id_method,
                    id_material=id_material,
                    sampling_area=sampling_area,
                    sampling_point=sampling_point,
                    from_rl=item["from_rl"],
                    to_rl=item["to_rl"],
                    batch_code=item["batch_code"],
                    increments=item["increments"],
                    fraction=item["fraction"],
                    size=item["size"],
                    sample_weight=item["sample_weight"],
                    sample_number=item["sample_number"],
                    remark=item["remark"],
                    primer_raw=item["primer_raw"],
                    duplicate_raw=item["duplicate_raw"],
                    unit_truck=item["truck"],
                    kode_batch=kode_batch,
                    type=sample_type_final,
                    sampling_deskripsi=item["sampling_deskripsi"],
                    sample_dup=item["sample_dup"],
                    user=user,
                )

                to_create.append(obj)

                existing_sample_keys.add(db_key)
                existing_codes.add(code)

                if kode_batch:
                    existing_batch_keys.add((iup_id, kode_batch.casefold()))

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # 5. BULK CREATE
        if to_create:
            with transaction.atomic():
                SampleProductions.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res