"""The three numbers the arithmetic rules need, each behind its own cue.

A bare percentage in a news story is usually a party's vote share, so every extractor
demands a nearby cue ("entrevistas", "margen", "confianza"). Missing a real sample size
degrades to a warning downstream; inventing one from a vote share would produce a false
arithmetic finding, which is much worse.
"""

import re
from decimal import Decimal

from ficha_tecnica.extractor.numbers import (
    parse_margin_figure,
    parse_percentage,
    parse_spanish_number,
)

_SAMPLE_CUES_BEFORE = re.compile(
    r"(?:muestra\s+(?:de|fue\s+de)|n\s*=\s*|total\s+de|encuesta\s+(?:a|con)|realizadas?|"
    r"realizaron)\s*([\d.,]+)",
    re.IGNORECASE,
)
_SAMPLE_CUES_AFTER = re.compile(
    r"([\d.,]+)\s*(?:personas|entrevistas|encuestados|encuestadas|entrevistados|entrevistadas|"
    r"casos)\b",
    re.IGNORECASE,
)
_MARGIN_CUE = re.compile(
    r"(?:margen\s+de\s+error|error\s+muestral|margen\s+de|margen\s+máximo|±|\+/-|\+-)",
    re.IGNORECASE,
)
_CONFIDENCE_CUE = re.compile(
    r"(?:nivel\s+de\s+confianza|confianza\s+del?|con\s+una\s+confianza)",
    re.IGNORECASE,
)

_YEAR_CEILING = 3000  # a "sample" of 2026 people is far more likely a year
_MAX_SAMPLE_SIZE = 100_000


def extract_sample_size(text: str) -> int | None:
    """Number of interviews, requiring a sample-size cue next to the figure."""
    for pattern in (_SAMPLE_CUES_AFTER, _SAMPLE_CUES_BEFORE):
        for match in pattern.finditer(text):
            value = parse_spanish_number(match.group(1))
            if value is None or value != value.to_integral_value():
                continue
            size = int(value)
            if size < 10 or size > _MAX_SAMPLE_SIZE or size == _YEAR_CEILING:
                continue
            return size
    return None


def extract_margin(text: str) -> Decimal | None:
    """Declared margin of error in points, requiring a margin cue.

    The figure must itself look like a margin (``±2,8``, ``2,8 %``, ``4 puntos``) so a
    party's vote share further down the sentence is never read as the margin.
    """
    for cue in _MARGIN_CUE.finditer(text):
        figure = parse_margin_figure(text[cue.start() : cue.start() + 80])
        if figure is not None:
            return figure
    return None


def extract_confidence(text: str) -> Decimal | None:
    """Confidence level of the margin, requiring a confidence cue."""
    cue = _CONFIDENCE_CUE.search(text)
    if cue is None:
        return None
    window = text[cue.start() : cue.start() + 80]
    return parse_percentage(window)
