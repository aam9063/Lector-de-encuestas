"""Curated entity lists and voting-estimate spans (sections 6.1, 6.4 and 7.5).

Pollster and party variants come from ``config/pollsters.yaml`` and
``config/parties.yaml``. Every formation gets identical treatment: no rule names a
party, and the extractor never reproduces figures, it only locates spans so the
sanitizer (ENC-09) can mask them. Matching is case-insensitive, word-bounded and
accent-tolerant ("Simple Logica" still finds "Simple Lógica"); when two variants
overlap the longest one wins.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from ficha_tecnica.extractor.candidates import split_sentences
from ficha_tecnica.extractor.numbers import FIGURE_PATTERN

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"

EntityKind = Literal["pollster", "party"]
EstimateKind = Literal["figure", "seats"]


@dataclass(frozen=True)
class EntityEntry:
    """One curated list entry: canonical name plus the variants to match."""

    name: str
    variants: tuple[str, ...]


@dataclass(frozen=True)
class EntitySpan:
    """A located entity: ``text[start:end]`` reproduces the matched variant."""

    start: int
    end: int
    kind: EntityKind
    name: str
    variant: str


@dataclass(frozen=True)
class EstimateSpan:
    """A vote estimate cue found in a sentence that also names a formation.

    ``kind`` is ``"figure"`` for a percentage and ``"seats"`` for "escaños".
    """

    start: int
    end: int
    kind: EstimateKind


@dataclass(frozen=True)
class _Matcher:
    pattern: re.Pattern[str]
    kind: EntityKind
    name: str
    variant: str


_ACCENTLESS = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"})


def _char_class(ch: str) -> str:
    """Match the accented and the plain form of one letter, either casing."""
    lower = ch.lower()
    plain = lower.translate(_ACCENTLESS)
    if plain != lower:
        return f"[{re.escape(lower)}{re.escape(plain)}]"
    return re.escape(ch)


def _variant_pattern(variant: str) -> re.Pattern[str]:
    """Compile one variant: word-bounded, case-insensitive, accent-tolerant."""
    body = "".join(_char_class(ch) for ch in variant)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def _load_entries(filename: str, key: str) -> tuple[EntityEntry, ...]:
    with (_CONFIG_DIR / filename).open(encoding="utf-8") as stream:
        data: dict[str, list[dict[str, object]]] = yaml.safe_load(stream)
    return tuple(
        EntityEntry(name=item["name"], variants=tuple(item["variants"]))  # type: ignore[arg-type]
        for item in data[key]
    )


@lru_cache(maxsize=1)
def load_pollsters() -> tuple[EntityEntry, ...]:
    """Curated pollster list, canonical name first, variants as written in YAML."""
    return _load_entries("pollsters.yaml", "pollsters")


@lru_cache(maxsize=1)
def load_parties() -> tuple[EntityEntry, ...]:
    """Complete national party list; identical treatment for every formation."""
    return _load_entries("parties.yaml", "parties")


@lru_cache(maxsize=1)
def _matchers() -> tuple[_Matcher, ...]:
    matchers = [
        _Matcher(_variant_pattern(variant), "pollster", entry.name, variant)
        for entry in load_pollsters()
        for variant in entry.variants
    ] + [
        _Matcher(_variant_pattern(variant), "party", entry.name, variant)
        for entry in load_parties()
        for variant in entry.variants
    ]
    # Longest variant first so "Navarro Acuña Asociados" beats "Navarro Acuña".
    return tuple(sorted(matchers, key=lambda m: (-len(m.variant), m.variant)))


def find_entities(text: str) -> list[EntitySpan]:
    """Locate every curated entity: non-overlapping, longest variant first, ordered."""
    found: list[EntitySpan] = []
    for matcher in _matchers():
        for match in matcher.pattern.finditer(text):
            found.append(
                EntitySpan(match.start(), match.end(), matcher.kind, matcher.name, matcher.variant)
            )
    found.sort(key=lambda span: (span.start, -(span.end - span.start)))
    chosen: list[EntitySpan] = []
    for span in found:
        if chosen and span.start < chosen[-1].end:
            continue  # an earlier, longer variant already covers this range
        chosen.append(span)
    return chosen


# Vote estimate cues reuse the Spanish figure grammar (grouped thousands, decimal
# comma) so "1.200 escaños" is one figure, never two.
_VOTE_FIGURE = re.compile(rf"({FIGURE_PATTERN})\s*%", re.IGNORECASE)
_SEATS = re.compile(rf"({FIGURE_PATTERN})\s+escaños?", re.IGNORECASE)


def find_estimates(text: str) -> list[EstimateSpan]:
    """Vote estimate spans: a percentage or "escaños" in a sentence naming a formation.

    Co-occurrence is measured per sentence; a figure in a sentence without a formation
    is some other statistic and is never returned.
    """
    entities = find_entities(text)
    parties = [span for span in entities if span.kind == "party"]
    if not parties:
        return []
    spans: set[EstimateSpan] = set()
    for sentence in split_sentences(text):
        names_party = any(
            party.start >= sentence.start and party.end <= sentence.end for party in parties
        )
        if not names_party:
            continue
        window = text[sentence.start : sentence.end]
        cues: tuple[tuple[re.Pattern[str], EstimateKind], ...] = (
            (_VOTE_FIGURE, "figure"),
            (_SEATS, "seats"),
        )
        for cue, kind in cues:
            for match in cue.finditer(window):
                spans.add(
                    EstimateSpan(sentence.start + match.start(), sentence.start + match.end(), kind)
                )
    return sorted(spans, key=lambda span: span.start)
