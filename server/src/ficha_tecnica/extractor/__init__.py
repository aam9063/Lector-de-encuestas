"""Deterministic extraction: Spanish number/date parser, item candidates, bounded digests."""

from ficha_tecnica.extractor.candidates import (
    SentenceSpan,
    all_candidates,
    candidates_for,
    checklist_item_ids,
    split_sentences,
)
from ficha_tecnica.extractor.dates import MONTHS, parse_date, parse_date_range
from ficha_tecnica.extractor.entities import (
    EntityEntry,
    EntitySpan,
    EstimateSpan,
    find_entities,
    find_estimates,
    load_parties,
    load_pollsters,
)
from ficha_tecnica.extractor.metrics import extract_confidence, extract_margin, extract_sample_size
from ficha_tecnica.extractor.numbers import (
    parse_margin_figure,
    parse_percentage,
    parse_spanish_number,
)

__all__ = [
    "MONTHS",
    "EntityEntry",
    "EntitySpan",
    "EstimateSpan",
    "SentenceSpan",
    "all_candidates",
    "candidates_for",
    "checklist_item_ids",
    "extract_confidence",
    "extract_margin",
    "extract_sample_size",
    "find_entities",
    "find_estimates",
    "load_parties",
    "load_pollsters",
    "parse_date",
    "parse_date_range",
    "parse_margin_figure",
    "parse_percentage",
    "parse_spanish_number",
    "split_sentences",
]
