"""Spanish date parsing for fieldwork periods.

The news text rarely carries a year ("del 3 al 9 de noviembre"), so the caller supplies
the reference year. A range that ends in an earlier month than it starts crosses the
year boundary ("del 28 de diciembre al 3 de enero").
"""

import re
from datetime import date

MONTHS: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# Abbreviations seen in Spanish press copy.
_MONTH_ALIASES: dict[str, int] = {
    **MONTHS,
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "sept": 9,
    "set": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

_MONTH = r"[a-záéíóúñ]+"

# "del 30 de octubre al 2 de noviembre": both months stated.
_RANGE_BOTH_MONTHS = re.compile(
    rf"\b(\d{{1,2}})\s+de\s+({_MONTH})\.?\s+(?:al|y|hasta\s+el)\s+(\d{{1,2}})\s+de\s+({_MONTH})\.?"
)
# "del 3 al 9 de noviembre", "entre el 3 y el 9 de noviembre", "3-9 de noviembre":
# only the end month is stated.
_RANGE_ONE_MONTH = re.compile(
    rf"\b(\d{{1,2}})\s*(?:al|y|hasta|-)\s*(?:el\s+)?(\d{{1,2}})\s+de\s+({_MONTH})\.?"
)
_SINGLE_DATE = re.compile(rf"\b(\d{{1,2}})\s+de\s+({_MONTH})\.?(?:\s+de\s+(\d{{4}}))?")


def _month(token: str) -> int | None:
    return _MONTH_ALIASES.get(token.lower().rstrip("."))


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date_range(text: str, year: int) -> tuple[date, date] | None:
    """Find the first fieldwork range in ``text``, or return ``None``."""
    both = _RANGE_BOTH_MONTHS.search(text)
    if both is not None:
        start_month = _month(both.group(2))
        end_month = _month(both.group(4))
        if start_month is None or end_month is None:
            return None
        start = _safe_date(year, start_month, int(both.group(1)))
        end_year = year + 1 if end_month < start_month else year
        end = _safe_date(end_year, end_month, int(both.group(3)))
        if start is None or end is None or end < start:
            return None
        return start, end

    one = _RANGE_ONE_MONTH.search(text)
    if one is not None:
        month = _month(one.group(3))
        if month is None:
            return None
        start = _safe_date(year, month, int(one.group(1)))
        end = _safe_date(year, month, int(one.group(2)))
        if start is None or end is None or end < start:
            return None
        return start, end

    return None


def parse_date(text: str, year: int) -> date | None:
    """Find the first single date in ``text``, honouring an explicit year."""
    match = _SINGLE_DATE.search(text)
    if match is None:
        return None
    month = _month(match.group(2))
    if month is None:
        return None
    explicit_year = match.group(3)
    return _safe_date(int(explicit_year) if explicit_year else year, month, int(match.group(1)))
