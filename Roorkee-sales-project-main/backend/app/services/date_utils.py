import datetime as dt


def months_ago_start(months: int, *, today: dt.date | None = None) -> dt.date:
    """First day of the month that is `months - 1` months before the current month.

    E.g. months=12 on 2026-07-12 returns 2025-08-01 (a rolling 12-month window
    including the current, partial month).
    """
    today = today or dt.date.today()
    year = today.year
    month = today.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    return dt.date(year, month, 1)
