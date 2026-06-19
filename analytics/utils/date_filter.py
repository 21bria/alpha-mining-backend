from datetime import datetime, timedelta


def get_week_range(year=None, month=None, week=None, as_date=False):
    if not week:
        raise ValueError("week wajib diisi")

    if "-" in str(week):
        year_str, week_str = str(week).split("-")
        iso_year = int(year_str)
        iso_week = int(week_str)

        start_date = datetime.strptime(
            f"{iso_year}-W{iso_week:02}-1",
            "%G-W%V-%u"
        )
        end_date = start_date + timedelta(days=6)

    elif year and not month:
        iso_year = int(year)
        iso_week = int(week)

        start_date = datetime.strptime(
            f"{iso_year}-W{iso_week:02}-1",
            "%G-W%V-%u"
        )
        end_date = start_date + timedelta(days=6)

    elif year and month:
        year = int(year)
        month = int(month)
        week = int(week)

        first_day = datetime(year, month, 1)
        start_date = first_day + timedelta(days=(week - 1) * 7)
        end_date = start_date + timedelta(days=6)

        if end_date.month != month:
            next_month = datetime(year, month, 28) + timedelta(days=4)
            end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

    else:
        raise ValueError("year wajib diisi jika week bukan format ISO")

    if as_date:
        return start_date.date(), end_date.date()

    return start_date, end_date