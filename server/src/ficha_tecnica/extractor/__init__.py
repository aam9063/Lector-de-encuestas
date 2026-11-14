"""Deterministic extraction: Spanish number/date parser, item candidates, bounded digests."""

from ficha_tecnica.extractor.dates import MONTHS, parse_date, parse_date_range
from ficha_tecnica.extractor.metrics import extract_confidence, extract_margin, extract_sample_size
from ficha_tecnica.extractor.numbers import (
    parse_margin_figure,
    parse_percentage,
    parse_spanish_number,
)

__all__ = [
    "MONTHS",
    "extract_confidence",
    "extract_margin",
    "extract_sample_size",
    "parse_date",
    "parse_date_range",
    "parse_margin_figure",
    "parse_percentage",
    "parse_spanish_number",
]
