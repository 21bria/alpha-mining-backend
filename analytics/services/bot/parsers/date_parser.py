# analytics/services/bot/parsers/date_parser.py

from datetime import timedelta
from django.utils.timezone import now
import re


MONTHS_ID = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12,
}


def parse_date_id(day, month_name, year=None):

    today = now().date()

    month = MONTHS_ID.get(month_name.lower())

    if not month:
        return None

    year = int(year) if year else today.year

    return f"{year}-{month:02d}-{int(day):02d}"


def parse_date(message):

    today = now().date()

    text = message.lower()

    # today
    if "hari ini" in text:
        return {
            "filter_type": "daily",
            "filter_date": today.isoformat()
        }

    # yesterday
    if "kemarin" in text:
        d = today - timedelta(days=1)

        return {
            "filter_type": "daily",
            "filter_date": d.isoformat()
        }

    # week to date
    if any(k in text for k in ["wtd", "minggu ini", "week to date"]):

        iso = today.isocalendar()

        return {
            "filter_type": "weekly",
            "year": iso.year,
            "month": today.month,
            "week": f"{iso.year}-{iso.week:02d}"
        }

    # last week
    if "minggu lalu" in text:

        d = today - timedelta(days=7)

        iso = d.isocalendar()

        return {
            "filter_type": "weekly",
            "year": iso.year,
            "month": d.month,
            "week": f"{iso.year}-{iso.week:02d}"
        }
    
    # bulan april 2026 / month april 2026
    match_month_name = re.search(
        r"bulan\s+([a-zA-Z]+)\s+(\d{4})",
        text
    )

    if match_month_name:
        month_name, year = match_month_name.groups()
        month = MONTHS_ID.get(month_name.lower())

        if month:
            return {
                "filter_type": "monthly",
                "year": int(year),
                "month": month
            }
        
    # MTD
    if any(k in text for k in ["mtd", "bulan ini", "month to date"]):

        return {
            "filter_type": "monthly",
            "year": today.year,
            "month": today.month
        }

    # last month
    if "bulan lalu" in text:

        month = today.month - 1
        year = today.year

        if month <= 0:
            month = 12
            year -= 1

        return {
            "filter_type": "monthly",
            "year": year,
            "month": month
        }

    # 3 bulan lalu
    match_month = re.search(r"(\d+)\s+bulan lalu", text)

    if match_month:

        n = int(match_month.group(1))

        month = today.month - n
        year = today.year

        while month <= 0:
            month += 12
            year -= 1

        return {
            "filter_type": "monthly",
            "year": year,
            "month": month
        }

    # YTD
    if any(k in text for k in ["ytd", "tahun ini", "year to date"]):

        return {
            "filter_type": "yearly",
            "year": today.year
        }

    # 2 tahun lalu
    match_year = re.search(r"(\d+)\s+tahun lalu", text)

    if match_year:

        n = int(match_year.group(1))

        return {
            "filter_type": "yearly",
            "year": today.year - n
        }

    # tanggal range
    match_range = re.search(
        r"tanggal\s+(\d{1,2})\s+([a-zA-Z]+)(?:\s+(\d{4}))?\s+sampai\s+(\d{1,2})\s+([a-zA-Z]+)(?:\s+(\d{4}))?",
        text
    )

    if match_range:

        d1, m1, y1, d2, m2, y2 = match_range.groups()

        return {
            "filter_type": "range",
            "date_start": parse_date_id(d1, m1, y1),
            "date_end": parse_date_id(d2, m2, y2),
        }

    # default
    return {
        "filter_type": "monthly",
        "year": today.year,
        "month": today.month
    }