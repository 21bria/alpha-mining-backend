from datetime import datetime, date, time
from typing import Any


def norm(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def parse_flexible_date(value: Any) -> date | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    s = norm(value)
    if s in {"", "-", "None", "none", "NULL", "null"}:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"invalid date '{value}'")


def parse_flexible_time(value: Any) -> time | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.time()

    if isinstance(value, time):
        return value

    s = norm(value)
    if s in {"", "-", "None", "none", "NULL", "null"}:
        return None

    s = s.replace(".", ":")

    formats = [
        "%H:%M:%S",
        "%H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue

    raise ValueError(f"invalid time '{value}'")