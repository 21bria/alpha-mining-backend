from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from django.db import transaction
from django.db.models.functions import Lower

from master.models import MineIUP, BargeUnits
from selling.models import BargingPlan
from imports.utils.parsers import norm, parse_flexible_date
from imports.utils.json_safe import json_safe_dict
import re


def norm_or_none(value: Any) -> str | None:
    s = norm(value)
    return s if s else None


def to_float_safe(value: Any) -> float:
    if value in (None, "", "-", "nan"):
        return 0.0
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return 0.0


def to_int_safe(value: Any) -> int | None:
    if value in (None, "", "-", "nan"):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return None


def normalize_barge_name(value: Any) -> str:
    s = norm(value).upper()
    s = s.replace(".", " ")
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_barging_plan_code(iup_code: str | None = None) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    if iup_code:
        return f"BPLAN-{iup_code}-{ts}"
    return f"BPLAN-{ts}"


@dataclass
class ImportResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[tuple[int, dict[str, Any], str]] = field(default_factory=list)

    def add_error(self, row_no: int, row: dict[str, Any], msg: str) -> None:
        self.failed += 1
        self.errors.append((row_no, json_safe_dict(row), msg))

class BargingPlanTransposeImporter:
    META_COLUMNS = {"iup_code", "plan_date", "date_plan", "date", "tanggal"}

    def split_dynamic_column(self, col_name: str) -> tuple[str | None, str | None]:
        raw = str(col_name).strip()
        if "__" in raw:
            left, right = raw.rsplit("__", 1)
            metric = norm(right).lower()
            if metric in {"tonnage", "no"}:
                return left.strip(), metric
        return None, None

    def prettify_header(self, key: str) -> str:
        s = str(key).strip().replace("__", "_")
        s = s.replace("_", " ")
        s = " ".join(s.split())
        s = s.upper()

        if s.startswith("TB "):
            s = "TB. " + s[3:]

        return s.title().replace("Tb. ", "TB. ")

    def is_fake_header_row(self, row: dict[str, Any]) -> bool:
        raw_iup = row.get("iup_code")
        raw_date = row.get("plan_date") or row.get("date_plan") or row.get("date") or row.get("tanggal")

        if norm(raw_iup) or norm(raw_date):
            return False

        non_meta_values = [
            str(v).strip().lower()
            for k, v in row.items()
            if str(k).strip().lower() not in self.META_COLUMNS and v not in (None, "", "-")
        ]

        if not non_meta_values:
            return False

        return all(v in {"tonnage", "no"} for v in non_meta_values)

    def normalize_input_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Support:
        1. row sudah final:
           {
             "iup_code": "IUP-001",
             "plan_date": "02-Mar-25",
             "TB. Entebe Emerald 36__tonnage": 150,
             "TB. Entebe Emerald 36__no": None,
           }

        2. row mentah dari parser generic:
           header metric row:
           {
             "iup_code": None,
             "plan_date": None,
             "tb_entebe_emerald_36": "tonnage",
             "tb_entebe_megastar_72": "no",
           }

           lalu row data:
           {
             "iup_code": "IUP-001",
             "plan_date": "02-Mar-25",
             "tb_entebe_emerald_36": 150,
             "tb_entebe_megastar_72": 300,
           }
        """
        if not rows:
            return rows

        normalized: list[dict[str, Any]] = []
        pending_map: dict[str, tuple[str, str]] = {}

        for row in rows:
            # kalau row ini memang header metric kedua, simpan mapping lalu skip
            if self.is_fake_header_row(row):
                pending_map = {}

                for col, val in row.items():
                    col_l = str(col).strip().lower()
                    if col_l in self.META_COLUMNS:
                        continue

                    metric = str(val).strip().lower() if val not in (None, "", "-") else ""
                    if metric not in {"tonnage", "no"}:
                        continue

                    pretty_name = self.prettify_header(str(col))
                    pending_map[str(col)] = (pretty_name, metric)

                continue

            # kalau row sudah final, pakai langsung
            if any("__" in str(k) for k in row.keys()):
                normalized.append(row)
                continue

            # kalau ada pending_map, bentuk ulang row jadi format final
            if pending_map:
                new_row: dict[str, Any] = {
                    "iup_code": row.get("iup_code"),
                    "plan_date": row.get("plan_date") or row.get("date_plan") or row.get("date") or row.get("tanggal"),
                }

                for col, val in row.items():
                    col_l = str(col).strip().lower()
                    if col_l in self.META_COLUMNS:
                        continue
                    if str(col) not in pending_map:
                        continue

                    pretty_name, metric = pending_map[str(col)]
                    new_row[f"{pretty_name}__{metric}"] = val

                normalized.append(new_row)
                continue

            normalized.append(row)

        return normalized

    def run(self, rows: list[dict[str, Any]], user=None) -> ImportResult:
        res = ImportResult()

        rows = self.normalize_input_rows(rows)

        parsed: list[dict[str, Any]] = []
        seen_file: set[tuple[str, str, str]] = set()

        iup_codes_needed: set[str] = set()
        barge_names_needed: set[str] = set()

        for row_no, row in enumerate(rows, start=1):
            try:
                if self.is_fake_header_row(row):
                    res.skipped += 1
                    continue

                raw_iup = row.get("iup_code")
                raw_date = row.get("plan_date") or row.get("date_plan") or row.get("date") or row.get("tanggal")

                iup_code = norm(raw_iup).upper() if raw_iup else ""
                plan_date = parse_flexible_date(raw_date)

                if not iup_code and not plan_date:
                    non_meta_values = [
                        v for k, v in row.items()
                        if str(k).strip().lower() not in self.META_COLUMNS and v not in (None, "", "-")
                    ]
                    if not non_meta_values:
                        res.skipped += 1
                        continue

                if not iup_code:
                    raise ValueError("iup_code is required")

                if not plan_date:
                    raise ValueError("plan_date is required")

                grouped: dict[str, dict[str, Any]] = {}

                for col, value in row.items():
                    if str(col).strip().lower() in self.META_COLUMNS:
                        continue

                    tugboat_name, metric = self.split_dynamic_column(str(col))
                    if not tugboat_name or not metric:
                        continue

                    tugboat_name_norm = normalize_barge_name(tugboat_name)
                    if not tugboat_name_norm:
                        continue

                    grouped.setdefault(tugboat_name_norm, {
                        "tugboat_name": tugboat_name.strip(),
                        "tonnage_plan": 0.0,
                        "no_plan": None,
                    })

                    if metric == "tonnage":
                        grouped[tugboat_name_norm]["tonnage_plan"] = to_float_safe(value)
                    elif metric == "no":
                        grouped[tugboat_name_norm]["no_plan"] = to_int_safe(value)

                found_any = False

                for tugboat_name_norm, item in grouped.items():
                    tonnage_plan = item["tonnage_plan"]
                    no_plan = item["no_plan"]

                    if tonnage_plan <= 0 and no_plan is None:
                        continue

                    found_any = True

                    file_key = (
                        iup_code.casefold(),
                        str(plan_date),
                        tugboat_name_norm.casefold(),
                    )
                    if file_key in seen_file:
                        raise ValueError(
                            f"duplicate in file: iup_code '{iup_code}', "
                            f"plan_date '{plan_date}', tugboat '{item['tugboat_name']}'"
                        )
                    seen_file.add(file_key)

                    parsed.append({
                        "row_no": row_no,
                        "raw": row,
                        "iup_code": iup_code,
                        "plan_date": plan_date,
                        "tugboat_name": item["tugboat_name"],
                        "tugboat_name_norm": tugboat_name_norm,
                        "tonnage_plan": tonnage_plan if tonnage_plan > 0 else None,
                        "no_plan": no_plan,
                        "description": "Import Excel Barging Plan",
                    })

                    iup_codes_needed.add(iup_code.casefold())
                    barge_names_needed.add(tugboat_name_norm.casefold())

                if not found_any:
                    res.skipped += 1

            except Exception as e:
                res.add_error(row_no, row, str(e))

        if not parsed:
            return res

        iup_map = {
            code_l: iup_id
            for code_l, iup_id in (
                MineIUP.objects
                .annotate(code_l=Lower("iup_code"))
                .filter(code_l__in=iup_codes_needed)
                .values_list("code_l", "id")
            )
        }
        barge_rows = BargeUnits.objects.values("id", "barge_code", "barge_name")

        barge_map_by_name = {}
        barge_map_by_code = {}

        for b in barge_rows:
            payload = {
                "id": b["id"],
                "barge_code": b["barge_code"],
                "barge_name": b["barge_name"],
            }

            norm_name = normalize_barge_name(b.get("barge_name"))
            norm_code = normalize_barge_name(b.get("barge_code"))

            if norm_name:
                barge_map_by_name[norm_name] = payload
            if norm_code:
                barge_map_by_code[norm_code] = payload

       
        db_iup_ids_needed = list(iup_map.values())
        existing_keys: set[tuple[int, str, str]] = set()

        if db_iup_ids_needed:
            existing_rows = (
                BargingPlan.objects
                .annotate(barge_code_l=Lower("barge_code"))
                .filter(iup_id__in=db_iup_ids_needed)
                .values_list("iup_id", "plan_date", "barge_code_l")
            )

            existing_keys = {
                (iup_id, str(plan_date), (barge_code_l or "").casefold())
                for iup_id, plan_date, barge_code_l in existing_rows
            }

        to_create: list[BargingPlan] = []
        model_fields = {f.name for f in BargingPlan._meta.fields}

        for item in parsed:
            row_no = item["row_no"]
            raw = item["raw"]

            try:
                iup_id = iup_map.get(item["iup_code"].casefold())
                if not iup_id:
                    raise ValueError(f"iup_code '{item['iup_code']}' not found")

                barge_obj = (
                    barge_map_by_name.get(item["tugboat_name_norm"])
                    or barge_map_by_code.get(item["tugboat_name_norm"])
                )

                if not barge_obj:
                    raise ValueError(
                        f"barge/tugboat '{item['tugboat_name']}' not found in master_barge"
                    )

                db_key = (
                    iup_id,
                    str(item["plan_date"]),
                    (barge_obj["barge_code"] or "").casefold(),
                )
                if db_key in existing_keys:
                    raise ValueError(
                        f"duplicate in DB: iup_code '{item['iup_code']}', "
                        f"plan_date '{item['plan_date']}', "
                        f"barge_code '{barge_obj['barge_code']}' already exists"
                    )

                data: dict[str, Any] = {
                    "code": build_barging_plan_code(item["iup_code"]),
                    "iup_id": iup_id,
                    "plan_date": item["plan_date"],
                    "tugboat_name": item["tugboat_name"],
                    "barge_code": barge_obj["barge_code"],
                    "tonnage_plan": item["tonnage_plan"],
                    "no_plan": item["no_plan"],
                    "description": item["description"],
                }

                if "id_user" in model_fields:
                    data["id_user"] = user.id if user and getattr(user, "id", None) else None

                to_create.append(BargingPlan(**data))
                existing_keys.add(db_key)

            except Exception as e:
                res.add_error(row_no, raw, str(e))

        if to_create:
            with transaction.atomic():
                BargingPlan.objects.bulk_create(to_create, batch_size=1000)
            res.success += len(to_create)

        return res