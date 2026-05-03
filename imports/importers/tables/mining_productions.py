from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.db.models.functions import Lower

from mining.models import mineProductions, mineAdditionFactor
from master.models import (
    MineIUP,
    SourceMinesLoading,
    SourceMinesDumping,
    SourceMinesDome,
    Material,
    MineUnits,
    Vendors,
)
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.converters import to_nullable_float, to_nullable_int
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def normalize_code(value: Any) -> str:
    s = norm(value).upper()
    return s.replace("_", "-").replace(" ", "-")


def parse_time_hauling(raw_value: Any) -> time | None:
    if raw_value in (None, ""):
        return None

    try:
        if str(raw_value).lower() == "nan":
            return None
    except Exception:
        pass

    if isinstance(raw_value, time):
        return raw_value

    if isinstance(raw_value, datetime):
        return raw_value.time()

    if isinstance(raw_value, float) and 0 <= raw_value < 1:
        try:
            excel_base = datetime(1899, 12, 30)
            return (excel_base + timedelta(days=raw_value)).time()
        except Exception:
            pass

    if isinstance(raw_value, int):
        try:
            val = str(int(raw_value)).zfill(4)
            return time(hour=int(val[:2]), minute=int(val[2:]))
        except Exception:
            pass

    if isinstance(raw_value, str):
        s = raw_value.strip()
        if not s:
            return None

        if s.isdigit():
            try:
                val = str(int(s)).zfill(4)
                return time(hour=int(val[:2]), minute=int(val[2:]))
            except Exception:
                pass

        for fmt in ("%H:%M", "%I:%M %p", "%H%M", "%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).time()
            except Exception:
                continue

    return None


def build_mine_code(iup_code: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{iup_code}-{ts}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class MiningProductionImporter:
    def run(self, rows: list[dict[str, Any]], user=None, task_id=None) -> ImportResult:
        res = ImportResult()
        parsed: list[dict[str, Any]] = []

        iup_codes_needed: set[str] = set()
        loading_names_needed: set[str] = set()
        dumping_names_needed: set[str] = set()
        pile_ids_needed: set[str] = set()
        material_names_needed: set[str] = set()
        vendor_names_needed: set[str] = set()
        unit_vendors_needed: set[str] = set()

        today = date.today()

        # =========================================================
        # 1. VALIDATE + COLLECT
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                date_pds = parse_flexible_date(
                    row.get("date_production") or row.get("Date Production")
                )
                raw_time = row.get("time_hauling") or row.get("Time Hauling")
                jam_ritase = parse_time_hauling(raw_time)

                iup_code = upper_or_none(row.get("iup_code") or row.get("IUP Code"))
                vendors = norm_or_none(row.get("vendors") or row.get("Vendors"))
                shift = upper_or_none(row.get("shift") or row.get("Shift"))
                loader = normalize_code(row.get("loader") or row.get("Loader")) if (row.get("loader") or row.get("Loader")) else None
                parsing = to_nullable_float(row.get("parsing") or row.get("Parsing"))

                hauler_class = norm_or_none(
                    row.get("hauler_class")
                    or row.get("loader_class")
                    or row.get("Hauler Class")
                    or row.get("Loader Class")
                )

                hauler = normalize_code(row.get("hauler") or row.get("Hauler")) if (row.get("hauler") or row.get("Hauler")) else None
                loading_point = norm_or_none(
                    row.get("loading_point") or row.get("Loading Point")
                )
                dumping_point = norm_or_none(
                    row.get("dumping_point") or row.get("Dumping Point")
                )
                pile_id = norm_or_none(row.get("pile_id") or row.get("Pile ID"))
                material_name = norm_or_none(row.get("material") or row.get("Material"))
                category_mine = norm_or_none(row.get("category") or row.get("Category"))
                distance = to_nullable_float(row.get("distance") or row.get("Distance"))
                block = norm_or_none(row.get("block_id") or row.get("Block Id"))
                rl_from = norm_or_none(row.get("from") or row.get("From Rl"))
                rl_to = norm_or_none(row.get("to") or row.get("To Rl"))
                ritase = to_nullable_int(row.get("ritase") or row.get("Ritase"))
                direct = norm_or_none(row.get("direct") or row.get("Direct"))
                remarks = norm_or_none(row.get("remarks") or row.get("Remarks"))

                required_fields = {
                    "iup_code": iup_code,
                    "date_production": date_pds,
                    "shift": shift,
                    "loading_point": loading_point,
                    "dumping_point": dumping_point,
                    "material": material_name,
                    "loader_class": hauler_class,
                }

                missing_fields = [
                    field_name for field_name, value in required_fields.items() if not value
                ]
                if missing_fields:
                    raise ValueError("required fields missing: " + ", ".join(missing_fields))

                if date_pds > today:
                    raise ValueError(
                        f"date_production '{date_pds}' cannot be greater than today '{today}'"
                    )

                parsing = 0 if parsing is None else parsing
                ritase = 0 if ritase is None else ritase

                ref_plan = f"{date_pds}{category_mine or ''}{vendors or ''}".replace(" ", "")
                left_date = date_pds.day if date_pds else None
                left_loading = str(jam_ritase.hour).zfill(2) if jam_ritase else None

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "date_pds": date_pds,
                    "raw_time": raw_time,
                    "time_loading": jam_ritase,
                    "vendors": vendors,
                    "shift": shift,
                    "loader": loader,   # sekarang dianggap unit_vendor
                    "parsing": parsing,
                    "hauler_class": hauler_class,
                    "hauler": hauler,   # sekarang dianggap unit_vendor
                    "loading_point": loading_point,
                    "dumping_point": dumping_point,
                    "pile_id": pile_id,
                    "material_name": material_name,
                    "category_mine": category_mine,
                    "distance": distance,
                    "block": block,
                    "rl_from": rl_from,
                    "rl_to": rl_to,
                    "ritase": ritase,
                    "direct": direct,
                    "remarks": remarks,
                    "ref_plan": ref_plan,
                    "left_date": left_date,
                    "left_loading": left_loading,
                })

                iup_codes_needed.add(iup_code.casefold())
                loading_names_needed.add(loading_point.casefold())
                dumping_names_needed.add(dumping_point.casefold())

                if vendors:
                    vendor_names_needed.add(vendors.casefold())
                if pile_id:
                    pile_ids_needed.add(pile_id.casefold())
                if material_name:
                    material_names_needed.add(material_name.casefold())
                if loader:
                    unit_vendors_needed.add(loader.casefold())
                if hauler:
                    unit_vendors_needed.add(hauler.casefold())

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        # =========================================================
        # 2. RESOLVE MASTER DATA
        # =========================================================
        iup_map = {
            code_l: obj_id
            for code_l, obj_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }

        vendor_map = {
            name_l: {
                "id": obj_id,
                "code": code,
                "vendor_name": vendor_name,
            }
            for name_l, obj_id, code, vendor_name in (
                Vendors.objects
                .annotate(name_l=Lower("code"))
                .filter(name_l__in=vendor_names_needed)
                .values_list("name_l", "id", "code", "vendor_name")
            )
        }

        loading_map = {
            name_l: {"id": obj_id, "source_id": source_id}
            for name_l, obj_id, source_id in (
                SourceMinesLoading.objects
                .annotate(name_l=Lower("loading_point"))
                .filter(name_l__in=loading_names_needed)
                .values_list("name_l", "id", "source_id")
            )
        }

        dumping_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SourceMinesDumping.objects
                .annotate(name_l=Lower("dumping_point"))
                .filter(name_l__in=dumping_names_needed)
                .values_list("name_l", "id")
            )
        }

        dome_map = {
            pile_id_l: obj_id
            for pile_id_l, obj_id in (
                SourceMinesDome.objects
                .annotate(pile_id_l=Lower("pile_id"))
                .filter(pile_id_l__in=pile_ids_needed)
                .values_list("pile_id_l", "id")
            )
        }

        unit_map = {
            unit_vendor_l: {
                "id": obj_id,
                "unit_class": unit_class,
                "unit_model": unit_model,
                "unit_vendor": unit_vendor,
                "unit_code": unit_code,
            }
            for unit_vendor_l, obj_id, unit_class, unit_model, unit_vendor, unit_code in (
                MineUnits.objects
                .annotate(unit_vendor_l=Lower("unit_vendor"))
                .filter(unit_vendor_l__in=unit_vendors_needed)
                .values_list("unit_vendor_l", "id", "unit_class", "unit_model", "unit_vendor", "unit_code")
            )
        }

        material_map = {
            name_l: {
                "id": obj_id,
                "categories": categories,
            }
            for name_l, obj_id, categories in (
                Material.objects
                .annotate(name_l=Lower("name"))
                .filter(name_l__in=material_names_needed)
                .values_list("name_l", "id", "categories")
            )
        }

        resolved_iup_ids = set(iup_map.values())

        factor_loader_map = {
            (iup_id, str(type_unit).casefold())
            for iup_id, type_unit in (
                mineAdditionFactor.objects
                .filter(iup_id__in=resolved_iup_ids)
                .values_list("iup_id", "type_unit")
            )
            if type_unit
        }

        addition_factor_map = {
            (iup_id, str(type_unit).casefold(), str(material).casefold()): {
                "bucket_capacity": bucket_capacity,
                "density_lcm": density_lcm,
            }
            for iup_id, type_unit, material, bucket_capacity, density_lcm in (
                mineAdditionFactor.objects
                .filter(iup_id__in=resolved_iup_ids)
                .values_list(
                    "iup_id",
                    "type_unit",
                    "material",
                    "bucket_capacity",
                    "density_lcm",
                )
            )
            if type_unit and material
        }

        # =========================================================
        # 3. BUILD OBJECTS
        # =========================================================
        to_create: list[mineProductions] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                errors = []

                iup_id = (
                    iup_map.get(item["iup_code"].casefold())
                    if item["iup_code"] else None
                )

                vendor_obj = (
                    vendor_map.get(item["vendors"].casefold())
                    if item["vendors"] else None
                )

                loading_obj = (
                    loading_map.get(item["loading_point"].casefold())
                    if item["loading_point"] else None
                )
                id_loading = loading_obj["id"] if loading_obj else None
                id_source = loading_obj["source_id"] if loading_obj else None

                id_dumping = (
                    dumping_map.get(item["dumping_point"].casefold())
                    if item["dumping_point"] else None
                )

                id_dome = (
                    dome_map.get(item["pile_id"].casefold())
                    if item["pile_id"] else None
                )

                loader_obj = (
                    unit_map.get(item["loader"].casefold())
                    if item["loader"] else None
                )
                hauler_obj = (
                    unit_map.get(item["hauler"].casefold())
                    if item["hauler"] else None
                )

                material_obj = (
                    material_map.get(item["material_name"].casefold())
                    if item["material_name"] else None
                )
                id_material = material_obj["id"] if material_obj else None
                material_category = material_obj["categories"] if material_obj else None

                if item["iup_code"] and iup_id is None:
                    errors.append(f"iup_code '{item['iup_code']}' not found")

                # vendor kerja boleh ada, tapi tidak dipakai untuk map unit
                if item["vendors"] and vendor_obj is None:
                    errors.append(f"vendors '{item['vendors']}' not found")

                if item["loading_point"] and id_loading is None:
                    errors.append(f"loading_point '{item['loading_point']}' not found")

                if item["loader"] and loader_obj is None:
                    errors.append(f"loader/unit_vendor '{item['loader']}' not found in master unit")

                if item["hauler"] and hauler_obj is None:
                    errors.append(f"hauler/unit_vendor '{item['hauler']}' not found in master unit")

                if item["dumping_point"] and id_dumping is None:
                    errors.append(f"dumping_point '{item['dumping_point']}' not found")

                if item["material_name"] and id_material is None:
                    errors.append(f"material '{item['material_name']}' not found")

                if item["pile_id"] and id_dome is None:
                    errors.append(f"pile_id '{item['pile_id']}' not found")

                if (
                    material_category
                    and str(material_category).strip().upper() == "ORE"
                    and not item["pile_id"]
                ):
                    errors.append(
                        f"pile_id is required for ORE material '{item['material_name']}'"
                    )

                addition = None
                loader_factor_key = (
                    iup_id,
                    str(item["hauler_class"] or "").casefold(),
                )

                if iup_id and item["hauler_class"]:
                    if loader_factor_key not in factor_loader_map:
                        errors.append(
                            f"loader_class '{item['hauler_class']}' not found in addition factor for iup '{item['iup_code']}'"
                        )
                    else:
                        factor_key = (
                            iup_id,
                            str(item["hauler_class"] or "").casefold(),
                            str(item["material_name"] or "").casefold(),
                        )
                        addition = addition_factor_map.get(factor_key)

                        if not addition:
                            errors.append(
                                f"addition factor not found for "
                                f"iup='{item['iup_code']}', "
                                f"loader_class='{item['hauler_class']}', "
                                f"material='{item['material_name']}'"
                            )

                if errors:
                    raise ValueError("; ".join(errors))

                bucket_capacity = addition.get("bucket_capacity", 0) or 0
                density_lcm = addition.get("density_lcm", 0) or 0

                tonnage_final = (
                    float(item["parsing"] or 0)
                    * float(item["ritase"] or 0)
                    * float(bucket_capacity)
                    * float(density_lcm)
                )

                code = build_mine_code(item["iup_code"])

                obj = mineProductions(
                    iup_id=iup_id,
                    code=code,
                    date_production=item["date_pds"],
                    vendors=item["vendors"],  # vendor kerja
                    shift=item["shift"],
                    loader=item["loader"],    # sekarang isi unit_vendor dari file
                    bucket=item["parsing"],
                    hauler_class=item["hauler_class"],
                    hauler=item["hauler"],    # sekarang isi unit_vendor dari file
                    sources_area=id_source,
                    loading_point=id_loading,
                    dumping_point=id_dumping,
                    dome_id=id_dome,
                    category_mine=material_category or item["category_mine"],
                    time_loading=item["time_loading"],
                    left_loading=item["left_loading"],
                    from_rl=item["rl_from"],
                    to_rl=item["rl_to"],
                    block_id=item["block"],
                    id_material=id_material,
                    ritase=item["ritase"],
                    bcm=0,
                    tonnage=tonnage_final,
                    direct=item["direct"],
                    remarks=item["remarks"],
                    hauler_type=None,
                    ref_materials=item["ref_plan"],
                    user=user if hasattr(mineProductions, "user") else None,
                )

                to_create.append(obj)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 4. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                mineProductions.objects.bulk_create(to_create, batch_size=1000)
            res.success += len(to_create)

        return res