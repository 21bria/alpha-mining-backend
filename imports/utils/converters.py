from typing import Any


def to_nullable_float(value: Any) -> float | None:
    if value is None:
        return None

    s = str(value).strip()

    if s in {"", "-", "None", "none", "NULL", "null"}:
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

    if s in {"", "-", "None", "none", "NULL", "null"}:
        return None

    try:
        return int(float(s))
    except ValueError:
        raise ValueError(f"invalid integer '{value}'")