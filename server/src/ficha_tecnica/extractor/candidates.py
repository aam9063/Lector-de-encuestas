"""Sentence splitting with original-text positions and per-item candidate phrases.

The checklist (``config/checklist.v1.yaml``) drives the item ids; every item has a set
of Spanish cue patterns. A candidate is a whole sentence located on the ORIGINAL text:
a consumer can always do ``text[start:end]`` and get the sentence back. Nothing is
interpreted here — locating evidence is ENC-04, reading it is the policy's job.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


@dataclass(frozen=True)
class SentenceSpan:
    """A sentence on the original text: ``text[start:end]`` reproduces it."""

    start: int
    end: int


# A sentence body runs to a terminator, but a dot followed by a digit is thousands
# grouping ("1.200") or a decimal, never a sentence end.
_SENTENCE = re.compile(r"(?:[^.!?…\n]|\.(?=\d))+[.!?…]*")

# Spanish press copy is full of abbreviations, and every one of them carries a dot that is
# not a terminator: "Demoscopia Ficticia S.L., cuya sede..." must stay one sentence, not
# "…Ficticia S." plus "L. , cuya sede…". That corrupted state is what made the live model
# classify an obvious poll as not_a_poll and grey out the whole sheet.
_ABBREVIATIONS = re.compile(
    r"(?<!\w)(?:S\.L\.U|S\.L|S\.A\.U|S\.A|EE\.UU|U\.S\.A|p\.\s?ej|n\.º|núm|pág|aprox|"
    r"etc|Srta|Sra|Sr|Dra|Dr|Uds|Ud|Vds|Vd)\.",
    re.IGNORECASE,
)

#: A character the sentence regex never treats as a terminator. Replacing a dot with it
#: keeps every index valid on the original text, so evidence spans still slice the input.
_PROTECTED_DOT = "\u0001"


def _protect_abbreviations(text: str) -> str:
    """Hide the dots inside known abbreviations without changing the length."""
    return _ABBREVIATIONS.sub(lambda match: match.group(0).replace(".", _PROTECTED_DOT), text)


# Spanish press copy carries accents, but a social-media style thread often drops
# them, and the same story must find the same evidence either way. Folding is 1:1 per
# character (every accented letter maps to one plain letter), so folded and original
# positions coincide and a span always slices the original text.
_ACCENT_FOLD = str.maketrans(
    {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ü": "U",
        "Ñ": "N",
    }
)

# Cues are written WITHOUT accents because they are matched against the folded text.
# Each cue is a whole regex; word boundaries keep a cue from matching inside a word.
_CUES: dict[str, tuple[re.Pattern[str], ...]] = {
    "a_entity": (
        re.compile(r"\b(?:realizad[ao]s?|elaborad[ao]s?|encargad[ao]s?)\s+(?:por|para)\b"),
        re.compile(r"\bsegun\b"),
        re.compile(r"\b(?:sondeo|encuesta|estudio)\s+de\b"),
    ),
    "a_entity_address": (re.compile(r"\b(?:sede|domicilio|calle|avenida|paseo)\b"),),
    "a_client": (
        re.compile(r"\b(?:por\s+encargo\s+de|a\s+peticion\s+de|promovid[ao]s?|contratad[ao]s?)\b"),
        re.compile(r"\bencargad[ao]s?\b"),
    ),
    "a_sample_size": (
        re.compile(r"\b(?:entrevistas?|entrevistad[ao]s?|encuestad[ao]s?|personas|casos)\b"),
        re.compile(r"\bmuestra\b"),
        re.compile(r"\bn\s*=\s*\d"),
    ),
    "a_margin": (
        re.compile(r"\b(?:margen\s+de\s+error|error\s+muestral|margen\s+maximo)\b"),
        re.compile(r"(?:±|\+/-|\+-)"),
    ),
    "a_confidence": (
        re.compile(r"\b(?:nivel\s+de\s+confianza|confianza\s+del?|con\s+una\s+confianza)\b"),
    ),
    "a_universe": (
        # The universe is stated in many ways: "residentes en la comunidad" is the explicit
        # form, but "personas con derecho a voto de la comunidad" says the same thing. The
        # paraphrase that dropped this cue produced a false accusation in the benchmark.
        re.compile(
            r"\b(?:universo|poblacion|mayores\s+de|residentes\s+en|\d+\s+anos|"
            r"derecho\s+a\s+voto|electores|electorado|censo|comunidad\s+autonoma)\b"
        ),
    ),
    "a_sampling_system": (
        re.compile(r"\b(?:muestreo|estratificad[ao]s?|afijacion|cuotas?|aleatori[ao]s?|panel)\b"),
    ),
    "a_selection_procedure": (
        re.compile(r"\b(?:seleccionad[ao]s?|contactad[ao]s?|marcacion|llamadas?)\b"),
    ),
    "a_mode": (
        re.compile(r"\b(?:telefon[oa]s?|presencial(?:es)?|cara\s+a\s+cara|online|internet)\b"),
    ),
    "a_fieldwork_dates": (
        re.compile(r"\btrabajos?\s+de\s+campo\b"),
        re.compile(r"\b(?:entre\s+el|del?)\s+\d{1,2}\b"),
        re.compile(r"\b\d{1,2}\s+de\s+[a-z]+\b"),
    ),
    "a_question_text": (re.compile(r"\b(?:pregunta|cuestionario)\b"),),
    "a_nonresponse": (
        # A response rate states nonresponse (100 - rate) even when the story never writes
        # "no contestó". Found by the evaluation: a paraphrase of "la tasa de respuesta fue
        # del 97 %" as "respondieron 97 de cada 100" made the app accuse the story of
        # omitting the datum. With a candidate present the asymmetry forbids accusing.
        re.compile(
            r"\b(?:no\s+(?:respond|contest)|tasa\s+de\s+respuesta|porcentaje\s+de\s+respuesta|"
            r"indice\s+de\s+respuesta|respondieron|no\s+respuesta)\b"
        ),
    ),
    "a_weighting": (re.compile(r"\bponderad[ao]s?\b|\bponderacion\b|\bpondera\b"),),
    "a_external_sheet": (re.compile(r"\b(?:ficha|hoja)\s+tecnica\b"),),
}


# Cues are matched case-insensitively. A cue word can open a sentence -- "Respondieron 97
# de cada 100 contactados" -- and a case-sensitive table missed those silently, which showed
# up as a false accusation in the evaluation.
_CUES = {
    item_id: tuple(re.compile(pattern.pattern, re.IGNORECASE) for pattern in patterns)
    for item_id, patterns in _CUES.items()
}


def _fold(text: str) -> str:
    """Drop accents one character at a time so indices stay valid on the original."""
    return text.translate(_ACCENT_FOLD)


def split_sentences(text: str) -> list[SentenceSpan]:
    """Split Spanish prose into sentence spans located on the original text."""
    spans: list[SentenceSpan] = []
    for match in _SENTENCE.finditer(_protect_abbreviations(text)):
        body = match.group().lstrip()
        if not body.strip():
            continue  # a chunk made only of terminators is not a sentence
        start = match.start() + (match.end() - match.start() - len(body))
        spans.append(SentenceSpan(start, match.end()))
    return spans


@lru_cache(maxsize=1)
def checklist_item_ids() -> tuple[str, ...]:
    """Item ids of the live checklist v1, in checklist order."""
    with (_CONFIG_DIR / "checklist.v1.yaml").open(encoding="utf-8") as stream:
        data: dict[str, Any] = yaml.safe_load(stream)
    return tuple(item["id"] for item in data["items"])


def _matching_sentences(text: str, folded: str, item_id: str) -> list[SentenceSpan]:
    cues = _CUES.get(item_id, ())
    if not cues:
        return []
    return [
        sentence
        for sentence in split_sentences(text)
        if any(cue.search(folded[sentence.start : sentence.end]) for cue in cues)
    ]


def candidates_for(text: str, item_id: str) -> list[SentenceSpan]:
    """Sentences of ``text`` that match any cue of the checklist item.

    Fewer candidates is always the safe direction: an item whose cues match nothing
    returns an empty list, which downstream policy treats as "no evidence shown".
    """
    if item_id not in checklist_item_ids():
        raise ValueError(f"unknown checklist item: {item_id!r}")
    return _matching_sentences(text, _fold(text), item_id)


def all_candidates(text: str) -> dict[str, list[SentenceSpan]]:
    """Candidate sentences for every checklist item, keyed by item id."""
    folded = _fold(text)
    return {item_id: _matching_sentences(text, folded, item_id) for item_id in checklist_item_ids()}
