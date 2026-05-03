from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import date

from django.db import transaction
from django.db.models.functions import Lower
from datetime import datetime

from core.models.base import make_code
from master.models import (
    MineIUP,
    SourceMinesLoading,
    Block,
    Material,
    SourceMinesDumping,
    SourceMinesDome,
    OreTruckFactor,
)
from geology.models import OreProductions

from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.converters import to_nullable_float, to_nullable_int
from imports.utils.json_safe import json_safe_dict


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def upper_or_none(value: Any) -> str | None:
    s = norm(value)
    return s.upper() if s else None


def build_ore_code(iup_code: str) -> str:
    return make_code(iup_code, datetime.now().strftime("%Y%m%d%H%M%S%f"))


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))


class OreProductionImporter:
    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        parsed: list[dict[str, Any]] = []

        iup_codes_needed: set[str] = set()
        source_names_needed: set[str] = set()
        block_names_needed: set[str] = set()
        material_names_needed: set[str] = set()
        stockpile_names_needed: set[str] = set()
        dome_names_needed: set[str] = set()
        truck_types_needed: set[str] = set()

        today = date.today()

        # =========================================================
        # 1. VALIDATE + COLLECT
        # =========================================================
        for row_no, row in enumerate(rows, start=1):
            try:
                iup_code = upper_or_none(row.get("iup_code"))
                date_pds = parse_flexible_date(row.get("date_production"))
                shift = upper_or_none(row.get("shift"))
                category = norm_or_none(row.get("category"))
                source = norm_or_none(row.get("prospect_area"))
                block = norm_or_none(row.get("mine_block"))
                rl_from = norm_or_none(row.get("from"))
                rl_to = norm_or_none(row.get("to"))
                material_name = norm_or_none(row.get("material"))
                grade = to_nullable_float(row.get("ni_gradeex"))
                grade_control = norm_or_none(row.get("grade_control"))
                truck = norm_or_none(row.get("unit_truck"))
                stockpile = norm_or_none(row.get("stockpile"))
                dome = norm_or_none(row.get("pile_id"))
                batch = norm_or_none(row.get("batch_code"))
                increment = to_nullable_int(row.get("increment"))
                status_batch = norm_or_none(row.get("batch_status"))
                ritase = to_nullable_int(row.get("ritase"))
                tonnage_input = to_nullable_float(row.get("tonnage"))
                status_pile = norm_or_none(row.get("pile_status"))
                remarks = norm_or_none(row.get("remarks"))
                ore_class = norm_or_none(row.get("ore_class"))
                truck_factors = norm_or_none(row.get("truck_factors"))

                required_fields = {
                    "iup_code": iup_code,
                    "date_production": date_pds,
                    "shift": shift,
                    "prospect_area": source,
                    # "mine_block": block,
                    "material": material_name,
                    "unit_truck": truck,
                    "stockpile": stockpile,
                    "pile_id": dome,
                    "batch_code": batch,
                    "truck_factors": truck_factors,
                }

                missing_fields = [field for field, value in required_fields.items() if not value]
                if missing_fields:
                    raise ValueError("required fields missing: " + ", ".join(missing_fields))

                if date_pds > today:
                    raise ValueError(
                        f"date_production '{date_pds}' cannot be greater than today '{today}'"
                    )

                grade = 0 if grade is None else grade
                increment = 0 if increment is None else increment
                ritase = 0 if ritase is None else ritase

                parsed.append({
                    "row_no": row_no,
                    "raw": row,
                    "iup_code": iup_code,
                    "date_pds": date_pds,
                    "shift": shift,
                    "category": category,
                    "source": source,
                    "block": block,
                    "rl_from": rl_from,
                    "rl_to": rl_to,
                    "material_name": material_name,
                    "grade": grade,
                    "grade_control": grade_control,
                    "truck": truck,
                    "stockpile": stockpile,
                    "dome": dome,
                    "batch": batch,
                    "increment": increment,
                    "status_batch": status_batch,
                    "ritase": ritase,
                    "tonnage_input": tonnage_input,
                    "status_pile": status_pile,
                    "remarks": remarks,
                    "ore_class": ore_class,
                })

                if iup_code:
                    iup_codes_needed.add(iup_code.casefold())
                if source:
                    source_names_needed.add(source.casefold())
                if block:
                    block_names_needed.add(block.casefold())
                if material_name:
                    material_names_needed.add(material_name.casefold())
                if stockpile:
                    stockpile_names_needed.add(stockpile.casefold())
                if dome:
                    dome_names_needed.add(dome.casefold())
                if truck:
                    truck_types_needed.add(truck.casefold())

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

        source_map = {
            name_l: obj_id
            for name_l, obj_id in (
                SourceMinesLoading.objects
                .annotate(name_l=Lower("loading_point"))
                .filter(name_l__in=source_names_needed)
                .values_list("name_l", "id")
            )
        }

        block_map = {
            name_l: obj_id
            for name_l, obj_id in (
                Block.objects
                .annotate(name_l=Lower("name"))
                .filter(name_l__in=block_names_needed)
                .values_list("name_l", "id")
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

        stockpile_map = {
            (iup_id, name_l): obj_id
            for iup_id, name_l, obj_id in (
                SourceMinesDumping.objects
                .annotate(name_l=Lower("dumping_point"))
                .filter(
                    iup_id__in=iup_map.values(),
                    name_l__in=stockpile_names_needed,
                )
                .values_list("iup_id", "name_l", "id")
            )
        }

        stockpile_ids = list(stockpile_map.values())
        dome_map = {
            (iup_id, dumping_id, pile_id_l): obj_id
            for iup_id, dumping_id, pile_id_l, obj_id in (
                SourceMinesDome.objects
                .annotate(pile_id_l=Lower("pile_id"))
                .filter(
                    iup_id__in=iup_map.values(),
                    dumping_id__in=stockpile_ids,
                    pile_id_l__in=dome_names_needed,
                )
                .values_list("iup_id", "dumping_id", "pile_id_l", "id")
            )
        }

        # =========================================================
        # 3. RESOLVE ORE TRUCK FACTOR
        # key = (iup_id, type_tf_l, material_id)
        # =========================================================
        truck_factor_map = {
            (iup_id, (type_tf or "").casefold(), material_id): ton
            for iup_id, type_tf, material_id, ton in (
                OreTruckFactor.objects
                .filter(
                    iup_id__in=iup_map.values(),
                    material_id__in=material_map.values(),
                )
                .values_list("iup_id", "type_tf", "material_id", "ton")
            )
        }

        # =========================================================
        # 4. BUILD OBJECTS
        # =========================================================
        to_create: list[OreProductions] = []

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                errors = []

                iup_id = iup_map.get(item["iup_code"].casefold())
                id_source = source_map.get(item["source"].casefold()) if item["source"] else None
                id_block = block_map.get(item["block"].casefold()) if item["block"] else None
                id_material = material_map.get(item["material_name"].casefold()) if item["material_name"] else None
                id_stockpile = (
                    stockpile_map.get((iup_id, item["stockpile"].casefold()))
                        if item["stockpile"] and iup_id
                        else None
                )

                id_pile = (
                    dome_map.get((iup_id, id_stockpile, item["dome"].casefold()))
                    if item["dome"] and iup_id and id_stockpile
                    else None
                )

                if not iup_id:
                    errors.append(f"iup_code '{item['iup_code']}' not found")
                if item["source"] and id_source is None:
                    errors.append(f"prospect_area '{item['source']}' not found")
                if item["block"] and id_block is None:
                    errors.append(f"mine_block '{item['block']}' not found")
                if item["material_name"] and id_material is None:
                    errors.append(f"material '{item['material_name']}' not found")
                if item["stockpile"] and id_stockpile is None:
                    errors.append(f"stockpile '{item['stockpile']}' not found")
                if item["dome"] and id_pile is None:
                    errors.append(
                        f"pile_id '{item['dome']}' not found for stockpile '{item['stockpile']}'"
                    )

                if errors:
                    raise ValueError("; ".join(errors))

                kode_batch = (
                    f"PDS"
                    f"{str(id_material or '')}"
                    f"{item['truck'] or ''}"
                    f"{str(id_stockpile or '')}"
                    f"{str(id_pile or '')}"
                    f"{item['batch'] or ''}"
                )

                code = build_ore_code(item["iup_code"])

                truck_type_lookup = (item.get("truck_factors") or item.get("truck") or "").casefold()

                factor_key = (
                    iup_id,
                    truck_type_lookup,
                    id_material,
                )
    
                factor_ton = truck_factor_map.get(factor_key)

                if factor_ton is None:
                    raise ValueError(
                        f"OreTruckFactor not found for iup='{item['iup_code']}', "
                        f"type_tf='{item['truck']}', material='{item['material_name']}'"
                    )
                
                ton_input = item.get("tonnage_input")
                # jika tonnage kosong atau 0 -> hitung dari factor
                if ton_input in (None, "", 0, "0"):
                    ritase_val = item.get("ritase")

                    if ritase_val in (None, "", 0, "0"):
                        tonnage_final = float(factor_ton)
                    else:
                        tonnage_final = float(factor_ton) * float(ritase_val)
                else:
                    tonnage_final = float(ton_input)

                # left_date = item["date_pds"].day if item["date_pds"] else None

                material_upper = (item["material_name"] or "").upper()
                if material_upper == "LIM":
                    sale_adjust = "HPAL"
                elif material_upper == "SAP":
                    sale_adjust = "RKEF"
                else:
                    sale_adjust = None

                obj = OreProductions(
                    iup_id=iup_id,
                    code=code,
                    tgl_production=item["date_pds"],
                    shift=item["shift"],
                    category=item["category"],
                    id_prospect_area=id_source,
                    id_block=id_block,
                    from_rl=item["rl_from"],
                    to_rl=item["rl_to"],
                    id_material=id_material,
                    grade_expect=item["grade"],
                    grade_control=item["grade_control"],
                    unit_truck=item["truck"],
                    id_stockpile=id_stockpile,
                    id_pile=id_pile,
                    batch_code=item["batch"],
                    increment=item["increment"],
                    batch_status=item["status_batch"],
                    ritase=item["ritase"],
                    tonnage=tonnage_final,
                    pile_status=item["status_pile"],
                    remarks=item["remarks"],
                    kode_batch=kode_batch,
                    pile_original=id_pile,
                    stockpile_ori=id_stockpile,
                    # left_date=left_date,
                    truck_factor=item["truck"],
                    ore_class=item["ore_class"],
                    status_dome="Continue",
                    sale_adjust=sale_adjust,
                    user=user if hasattr(OreProductions, "user") else None,
                )

                to_create.append(obj)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        # =========================================================
        # 5. BULK CREATE
        # =========================================================
        if to_create:
            with transaction.atomic():
                OreProductions.objects.bulk_create(to_create, batch_size=500)
            res.success += len(to_create)

        return res