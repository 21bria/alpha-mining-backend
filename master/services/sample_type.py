from typing import Any
from django.db.models import Q

from master.models import SampleType


def get_sample_types(usages: list[str]) -> set[str]:
    cond = Q()

    if "production" in usages:
        cond |= Q(is_production=True)

    if "geology" in usages:
        cond |= Q(is_geology=True)

    if "selling" in usages:
        cond |= Q(is_selling=True)

    if "monitoring" in usages:
        cond |= Q(is_monitoring=True)

    return {
        str(x).strip().upper()
        for x in SampleType.objects.filter(
            cond,
            status=1,
        ).values_list("type_sample", flat=True)
    }


def get_selling_type_names() -> set[str]:
    return {
        str(x).strip().upper()
        for x in SampleType.objects.filter(
            Q(is_selling=True) | Q(is_monitoring=True),
            status=1,
        ).values_list("type_sample", flat=True)
    }


def get_sample_type_map() -> dict[str, dict[str, Any]]:
    return {
        str(x["type_sample"]).strip().upper(): x
        for x in SampleType.objects.filter(status=1).values(
            "id",
            "type_sample",
            "is_production",
            "is_geology",
            "is_selling",
            "is_monitoring",
            "batch_pattern",
        )
    }

def get_production_geology_sample_type_map() -> dict[str, dict[str, Any]]:
    return {
        str(x["type_sample"]).strip().upper(): x
        for x in SampleType.objects.filter(
            Q(is_production=True) | Q(is_geology=True),
            status=1,
        ).values(
            "id",
            "type_sample",
            "is_production",
            "is_geology",
            "batch_pattern",
        )
    }

def get_selling_monitoring_sample_type_map() -> dict[str, dict[str, Any]]:
    return {
        str(x["type_sample"]).strip().upper(): x
        for x in SampleType.objects.filter(
            Q(is_selling=True) | Q(is_monitoring=True),
            status=1,
        ).values(
            "id",
            "type_sample",
            "is_selling",
            "is_monitoring",
            "batch_pattern",
        )
    }

def build_pattern(pattern: str | None, **kwargs) -> str | None:
    if not pattern:
        return None

    return pattern.format(
        type=kwargs.get("type", ""),
        material=kwargs.get("material", ""),
        truck=kwargs.get("truck", ""),
        point=kwargs.get("point", ""),
        pit_dome=kwargs.get("pit_dome", ""),
        batch=kwargs.get("batch", ""),
        increments=kwargs.get("increments", ""),
        lot=kwargs.get("lot", ""),
    )