import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from django.db.models import Q
from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP, Material,SampleMethod, SampleType,SellingCode,StockFactories
from geology.models import SampleProductions,QualityConfig
from core.models.base import make_code # lokasi function

from imports.utils.parsers import norm, parse_flexible_date, parse_flexible_time
from imports.utils.converters import to_nullable_float, to_nullable_int
from imports.utils.json_safe import json_safe_dict

from master.services.sample_type import (
    get_selling_monitoring_sample_type_map,
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


class SamplesSellingImporter:
    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        seen_sample: set[tuple[str, str]] = set()
        seen_kode_batch: set[tuple[Any, str]] = set()

        parsed: list[dict[str, Any]] = []

        iup_codes_needed: set[str] = set()
        material_names_needed: set[str] = set()
        method_names_needed: set[str] = set()
        type_names_needed: set[str] = set()
        code_lot_needed: set[str] = set()
        buyer_needed: set[str] = set()

        today = date.today()
        sample_type_map = get_selling_monitoring_sample_type_map()

        if not sample_type_map:
            res.add_error(0,{},"No active selling/monitoring sample types found. Please set is_selling=True or is_monitoring=True in SampleType master." )
            return res

        # 1. VALIDATE + COLLECT
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = norm(row.get("iup_code")).upper()
                shift = upper_or_none(row.get("shift"))
                tgl_sample = parse_flexible_date(row.get("date_sample"))
                sample_type_name = upper_or_none(row.get("sample_type"))
                sample_method_name = norm_or_none(row.get("sampling_method"))
                material_name = norm_or_none(row.get("material"))
                code_lot_name = norm_or_none(row.get("code_lot"))
                buyer_name = norm_or_none(row.get("buyer"))

                required_fields = {
                    "iup_code": iup_code,
                    "shift": shift,
                    "date_sample": tgl_sample,
                    "sample_type": sample_type_name,
                    "sampling_method": sample_method_name,
                    "material": material_name,
                    "code_lot": code_lot_name,
                    "buyer": buyer_name,
                }

                missing_fields = [
                    field for field, value in required_fields.items() if not value
                ]
                if missing_fields:
                    raise ValueError("required fields missing: " + ", ".join(missing_fields))

                if tgl_sample > today:
                    raise ValueError(
                        f"date_sample '{tgl_sample}' cannot be greater than today '{today}'"
                    )

                sample_type_cfg = sample_type_map.get( str(sample_type_name).strip().upper())

                if not sample_type_cfg:
                    raise ValueError(
                        f"sample_type '{sample_type_name}' is not active for selling/monitoring"
                    )

                batch_code = norm_or_none(row.get("sub_lot"))
                increments = to_nullable_int(row.get("group"))
                fraction = None
                size = None
                sample_weight = to_nullable_float(row.get("sample_weight"))
                sample_number = norm(row.get("sample_id")).upper()
                remark = norm_or_none(row.get("remark"))
                primer_raw = to_nullable_float(row.get("primer_raw"))
                duplicate_raw = to_nullable_float(row.get("duplicat_raw"))
                to_lab = parse_flexible_time(row.get("to_lab"))

                if not sample_number:
                    raise ValueError("sample_id is required")

                file_key = (iup_code.casefold(), sample_number.casefold())
                if file_key in seen_sample:
                    raise ValueError(
                        f"duplicate in file: iup_code '{iup_code}', sample_id '{sample_number}'"
                    )
                seen_sample.add(file_key)

                if increments is None:
                    increments = 0

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "tgl_sample": tgl_sample,
                    "shift": shift,
                    "sample_type_name": sample_type_name,
                    "sample_method_name": sample_method_name,
                    "material_name": material_name,
                    "buyer_name": buyer_name,
                    "code_lot_name": code_lot_name,
                    "batch_code": batch_code,
                    "increments": increments,
                    "fraction": fraction,
                    "size": size,
                    "sample_weight": sample_weight,
                    "sample_number": sample_number,
                    "remark": remark,
                    "primer_raw": primer_raw,
                    "duplicate_raw": duplicate_raw,
                    # "to_lab": to_lab,
                })

                iup_codes_needed.add(iup_code.casefold())
                material_names_needed.add(material_name.casefold())
                method_names_needed.add(sample_method_name.casefold())
                type_names_needed.add(sample_type_name.casefold())
                code_lot_needed.add(code_lot_name.casefold())
                buyer_needed.add(buyer_name.casefold())

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
                    Q(is_selling=True) | Q(is_monitoring=True),
                    name_l__in=type_names_needed,
                    status=1,
                )
                .values_list("name_l", "id")
            )
        }

        code_lot_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SellingCode.objects
                .annotate(name_l=Lower("code"))
                .filter(name_l__in=code_lot_needed)
                .values_list("name_l", "id")
            )
        }

        factory_map = {
            name_l: obj_id
            for name_l, obj_id in (
                StockFactories.objects
                .annotate(name_l=Lower("factory_stock"))
                .filter(name_l__in=buyer_needed)
                .values_list("name_l", "id")
            )
        }

        # 3. EXISTING CHECK
        db_iup_ids_needed = list(iup_map.values())

        existing_sample_keys: set[tuple[Any, str]] = set()
        existing_codes: set[str] = set()
        existing_kode_batch_keys: set[tuple[Any, str]] = set()

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

            existing_codes = set(
                SampleProductions.objects
                .filter(iup_id__in=db_iup_ids_needed)
                .exclude(code__isnull=True)
                .exclude(code="")
                .values_list("code", flat=True)
            )

            existing_kode_batch_rows = (
                SampleProductions.objects
                .annotate(kode_batch_l=Lower("kode_batch"))
                .filter(iup_id__in=db_iup_ids_needed)
                .exclude(kode_batch__isnull=True)
                .exclude(kode_batch="")
                .values_list("iup_id", "kode_batch_l")
            )
            existing_kode_batch_keys = {
                (iup_id, kode_batch_l)
                for iup_id, kode_batch_l in existing_kode_batch_rows
            }

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
                code_lot_name = item["code_lot_name"]
                buyer_name = item["buyer_name"]

                id_type_sample = type_map.get(sample_type_name.casefold()) if sample_type_name else None
                id_method = method_map.get(sample_method_name.casefold()) if sample_method_name else None
                id_material = material_map.get(material_name.casefold()) if material_name else None
                product_code_id = code_lot_map.get(code_lot_name.casefold()) if code_lot_name else None
                factory_id = factory_map.get(buyer_name.casefold()) if buyer_name else None

                if sample_type_name and id_type_sample is None:
                    errors.append(f"sample_type '{sample_type_name}' not found or not marked as selling/monitoring")
                if sample_method_name and id_method is None:
                    errors.append(f"sampling_method '{sample_method_name}' not found")
                if material_name and id_material is None:
                    errors.append(f"material '{material_name}' not found")
                if buyer_name and factory_id is None:
                    errors.append(f"buyer '{buyer_name}' not found")
                if code_lot_name and product_code_id is None:
                    errors.append(f"code_lot '{code_lot_name}' not found")

                if errors:
                    raise ValueError("; ".join(errors))

                # duplicate iup + sample_number
                db_key = (iup_id, item["sample_number"].casefold())
                if db_key in existing_sample_keys:
                    raise ValueError(
                        f"duplicate in DB: iup_code '{item['iup_code']}', "
                        f"sample_number '{item['sample_number']}' already exists"
                    )

                # duplicate code
                code = build_sample_code(item["iup_code"], item["sample_number"])
                if code in existing_codes:
                    raise ValueError(f"duplicate code in DB: '{code}' already exists")

                # selling logic
                sample_type_cfg = sample_type_map.get(str(sample_type_name or "").strip().upper() )

                if not sample_type_cfg:
                    raise ValueError(
                        f"sample_type '{sample_type_name}' is not active for selling/monitoring"
                    )

                pattern = sample_type_cfg.get("batch_pattern")

                generated_code = build_pattern(
                    pattern,
                    type=sample_type_name or "",
                    material=str(id_material or ""),
                    lot=code_lot_name or "",
                    batch=item["batch_code"] or "",
                    increments=item["increments"] or "",
                )

                if sample_type_cfg["is_selling"]:
                    kode_batch = generated_code
                    selling_pulp = (
                        f"{sample_type_name or ''}"
                        f"{code_lot_name or ''}"
                        f"{item['batch_code'] or ''}"
                    )
                    sale_monitoring = None

                elif sample_type_cfg["is_monitoring"]:
                    kode_batch = None
                    selling_pulp = None
                    sale_monitoring = generated_code

                else:
                    raise ValueError(
                        f"sample_type '{sample_type_name}' is not selling or monitoring"
                    )
                
                if kode_batch:
                    batch_key = (iup_id, kode_batch.casefold())

                    if batch_key in existing_kode_batch_keys:
                        raise ValueError(
                            f"duplicate kode_batch in DB: iup_code '{item['iup_code']}', "
                            f"kode_batch '{kode_batch}' already exists"
                        )

                    if batch_key in seen_kode_batch:
                        raise ValueError(
                            f"duplicate kode_batch in file: iup_code '{item['iup_code']}', "
                            f"kode_batch '{kode_batch}'"
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
                    product_code=product_code_id,
                    discharge_area=factory_id,
                    batch_code=item["batch_code"],
                    increments=item["increments"],
                    fraction=item["fraction"],
                    size=item["size"],
                    sample_weight=item["sample_weight"],
                    sample_number=item["sample_number"],
                    remark=item["remark"],
                    primer_raw=item["primer_raw"],
                    duplicate_raw=item["duplicate_raw"],
                    # to_its=item["to_lab"],
                    unit_truck=sample_type_name,
                    kode_batch=kode_batch,
                    type=sample_type_name,
                    selling_pulp=selling_pulp,
                    sale_monitoring=sale_monitoring,
                    sampling_deskripsi=None,
                    sample_dup=None,
                    user=user,
                )

                to_create.append(obj)
                existing_sample_keys.add(db_key)
                existing_codes.add(code)

                if kode_batch:
                    existing_kode_batch_keys.add((iup_id, kode_batch.casefold()))

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # 5. BULK CREATE
        if to_create:
            with transaction.atomic():
                SampleProductions.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res