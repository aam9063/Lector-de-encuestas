"""Independent detector for vote-estimate leaks (section 7.5).

This is the test oracle for the sanitizer, so it MUST NOT share the sanitizer's logic:
it has its own party matching, its own windowing (punctutation-terminated clauses, with
no special case for the dot inside ``1.200``) and its own figure grammar. If both sides
shared a blind spot, the suite would report zero leaks while the app still leaked.

It fails closed: a bare number in the same clause as a formation counts as a leak, even
when it is innocent ("el PP en 2019"). Being wrong in that direction costs an over-masked
sentence; being wrong in the other direction publishes a poll result.
"""

import re
from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"

#: A clause ends at any of these, deliberately including the dot inside "1.200".
_CLAUSE_END = re.compile(r"[.!?…\n]")
_DIGIT = re.compile(r"\d")
_MAX_CLAUSE_CHARS = 300


@lru_cache(maxsize=1)
def party_variants() -> tuple[str, ...]:
    """Every polled formation's name and variants, longest first."""
    with (_CONFIG_DIR / "parties.yaml").open(encoding="utf-8") as stream:
        data: dict[str, list[dict[str, object]]] = yaml.safe_load(stream)
    # The simulation formations are part of the list too, otherwise the detector would be
    # blind to exactly the corpus the evaluation uses to prove it works.
    parties = [*data["parties"], *data.get("simulation_parties", [])]
    variants = {
        str(variant)
        for party in parties
        for variant in [party["name"], *party["variants"]]  # type: ignore[misc]
    }
    return tuple(sorted(variants, key=lambda item: (-len(item), item)))


@lru_cache(maxsize=1)
def _party_pattern() -> re.Pattern[str]:
    escaped = "|".join(re.escape(variant) for variant in party_variants())
    return re.compile(rf"(?<!\w)(?:{escaped})(?!\w)", re.IGNORECASE)


def _clause(text: str, start: int, end: int) -> str:
    """The clause around a mention: bounded by terminators and by a hard length cap."""
    left = max(0, start - _MAX_CLAUSE_CHARS)
    right = min(len(text), end + _MAX_CLAUSE_CHARS)
    before = text[left:start]
    after = text[end:right]
    last_break = max((match.end() for match in _CLAUSE_END.finditer(before)), default=0)
    next_break = _CLAUSE_END.search(after)
    clause_start = left + last_break
    clause_end = end + (next_break.start() if next_break else len(after))
    return text[clause_start:clause_end]


def find_leaks(text: str) -> list[str]:
    """Every clause that puts a formation next to a figure. Empty list means clean."""
    if not text:
        return []
    leaks: list[str] = []
    for match in _party_pattern().finditer(text):
        clause = _clause(text, match.start(), match.end())
        if _DIGIT.search(clause):
            leaks.append(clause)
    return leaks
