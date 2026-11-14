"""Spanish number parsing.

Spain writes thousands with a dot and decimals with a comma, so ``1.200`` is one
thousand two hundred and ``2,8`` is two point eight. Getting this backwards would
turn a 1.200-person sample into a 1.2-person sample, so the rules are strict:

- a dot only groups thousands in blocks of exactly three digits;
- a comma is always the decimal separator;
- anything else is rejected instead of guessed.

Arithmetic later uses ``Decimal`` so margins and ratios do not pick up float noise.
"""

import re
from decimal import Decimal, InvalidOperation

_THOUSANDS = re.compile(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$")
_PLAIN_DECIMAL = re.compile(r"^\d+(?:,\d+)?$")

#: A figure with an optional thousands grouping and an optional decimal comma.
#: Ordered so the grouped form wins: 1.200 must not be read as 1.2.
FIGURE_PATTERN = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"

_PLUS_MINUS = re.compile(rf"(?:±|\+/-|\+-)\s*({FIGURE_PATTERN})")
_PERCENTAGE = re.compile(rf"({FIGURE_PATTERN})\s*%")
_POINTS = re.compile(rf"({FIGURE_PATTERN})\s*(?:puntos|punto)\b")
_MARGIN_FIGURE = re.compile(
    # The boundary belongs to "puntos", not to the whole group: after a "%" followed by a
    # space there is no word boundary, so `(?:%|puntos?)\b` made every margin written as a
    # plain percentage invisible. Found on a real article: "margen de error del 0,5%".
    rf"(?:±|\+/-|\+-)\s*({FIGURE_PATTERN})|({FIGURE_PATTERN})\s*(?:%|puntos?\b)"
)


def parse_spanish_number(raw: str) -> Decimal | None:
    """Parse a single Spanish-formatted number, or return ``None``."""
    text = raw.strip()
    if not text:
        return None
    if _THOUSANDS.match(text):
        return _to_decimal(_normalise(text))
    if _PLAIN_DECIMAL.match(text):
        return _to_decimal(_normalise(text))
    return None


def parse_percentage(text: str) -> Decimal | None:
    """Find the first percentage-like figure: ``2,8 %``, ``±2,8`` or ``3 puntos``."""
    for pattern in (_PLUS_MINUS, _PERCENTAGE, _POINTS):
        match = pattern.search(text)
        if match is not None:
            return _to_decimal(_normalise(match.group(1)))
    return None


def parse_margin_figure(text: str) -> Decimal | None:
    """Find a figure that is explicitly a margin: ``±2,8``, ``2,8 %`` or ``4 puntos``.

    A bare number is never a margin, which keeps a party's vote share out of the
    arithmetic rules.
    """
    match = _MARGIN_FIGURE.search(text)
    if match is None:
        return None
    return _to_decimal(_normalise(match.group(1) or match.group(2)))


def _normalise(figure: str) -> str:
    """Turn a Spanish figure into something ``Decimal`` accepts."""
    return figure.replace(".", "").replace(",", ".")


def _to_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except InvalidOperation, ValueError:  # pragma: no cover - regex-guarded
        return None
