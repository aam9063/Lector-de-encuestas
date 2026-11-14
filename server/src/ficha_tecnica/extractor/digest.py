"""Bounded digests A/B/C and the ``state`` string sent to Clef (section 6.2).

Clef accepts ~16k tokens, but less noise means better decisions and lower latency,
so each group gets its own bounded digest: A (technical sheet, 1200 tokens), B
(type and framing, 500 tokens, deliberately NOT sanitized — sanitizing is an
output concern, section 7.5) and C (wording, quoted questions only, 400 tokens).
Budgets are hard ceilings: a sentence that would push a digest over budget is
left out whole; sentences are never cut, except the lede, which is trimmed at a
word boundary.

Token counting here is a documented approximation: one token per 4 characters,
rounded up (``estimate_tokens``). It is deterministic, dependency-free and good
enough to bound noise; if exactness is ever needed, only that function changes.
"""

import json
import re
from collections.abc import Callable
from typing import Any

from ficha_tecnica.extractor.candidates import _fold, split_sentences

_BUDGET_A = 1200
_BUDGET_B = 500
_BUDGET_C = 400
_LEDE_TOKEN_BUDGET = 120
_MAX_FIGURE_SENTENCES = 6

_CHARS_PER_TOKEN = 4

#: Digest A keeps sentences carrying a digit or any of these cue stems, matched
#: against the accent-folded text (the stems are written without accents).
_TECHNICAL_CUES = re.compile(
    r"\b(?:muestra|entrevist|margen|error|campo|encuesta|ficha|universo|confianza)"
)

#: A quoted question sits inside quotation marks and carries a question mark. It is
#: read from INSIDE the quotes: the sentence splitter (candidates.py) terminates a
#: sentence at the question mark, so a quoted question is never a whole sentence.
_QUOTED_SPAN = re.compile(r"«([^»]+)»|\"([^\"]+)\"|“([^”]+)”")


def estimate_tokens(text: str) -> int:
    """Approximate token count: characters / 4, rounded up.

    This is a documented approximation, not a real tokenizer: deterministic,
    dependency-free and good enough to bound the noise sent to Clef. If exact
    counting is ever needed, replace only this function.
    """
    return -(-len(text) // _CHARS_PER_TOKEN)


def build_state(digest: dict[str, Any]) -> str:
    """Serialize one digest into the compact JSON string sent to Clef."""
    return json.dumps(digest, ensure_ascii=False, separators=(",", ":"))


def build_digest_a(text: str) -> dict[str, Any]:
    """Digest A: headline, lede and technical sentences (digits or cue words)."""
    return _digest_with_cues(text, "technical_sentences", _is_technical, _BUDGET_A, None)


def build_digest_b(text: str) -> dict[str, Any]:
    """Digest B: headline, lede and up to six figure sentences, without sanitizing."""
    return _digest_with_cues(
        text, "figure_sentences", _has_figures, _BUDGET_B, _MAX_FIGURE_SENTENCES
    )


def build_digest_c(text: str) -> dict[str, Any]:
    """Digest C: quoted questions only, nothing else."""
    picked: list[str] = []
    for question in _quoted_questions(text):
        trial = _with_meta({"quoted_questions": [*picked, question]}, len(text))
        if _tokens(trial) > _BUDGET_C:
            continue
        picked.append(question)
    return _with_meta({"quoted_questions": picked}, len(text))


def _digest_with_cues(
    text: str,
    list_key: str,
    keeps: Callable[[str], bool],
    budget: int,
    max_items: int | None,
) -> dict[str, Any]:
    """Headline + lede + the first sentences matching ``keeps`` within ``budget``."""
    texts = _sentence_texts(text)
    if not texts:
        return _with_meta({"headline": "", "lede": "", list_key: []}, len(text))
    headline = texts[0]
    lede, lede_sentences = _lede(texts[1:], _LEDE_TOKEN_BUDGET)
    seen = {headline, *lede_sentences}
    base: dict[str, Any] = {"headline": headline, "lede": lede}
    picked: list[str] = []
    for sentence in texts[1:]:
        if max_items is not None and len(picked) == max_items:
            break
        if sentence in seen or not keeps(sentence):
            continue
        trial = _with_meta({**base, list_key: [*picked, sentence]}, len(text))
        if _tokens(trial) > budget:
            continue
        picked.append(sentence)
        seen.add(sentence)
    return _with_meta({**base, list_key: picked}, len(text))


def _sentence_texts(text: str) -> list[str]:
    """Sentences of ``text`` as plain strings, in original order."""
    return [text[span.start : span.end] for span in split_sentences(text)]


def _has_figures(sentence: str) -> bool:
    return any(character.isdigit() for character in sentence)


def _is_technical(sentence: str) -> bool:
    return _has_figures(sentence) or _TECHNICAL_CUES.search(_fold(sentence)) is not None


def _quoted_questions(text: str) -> list[str]:
    """Questions quoted in the text (inside quotes, with a question mark), in order."""
    questions: list[str] = []
    for match in _QUOTED_SPAN.finditer(text):
        quoted = next(group for group in match.groups() if group is not None).strip()
        if "?" not in quoted or quoted in questions:
            continue
        questions.append(quoted)
    return questions


def _lede(sentences: list[str], token_budget: int) -> tuple[str, list[str]]:
    """The opening sentences within ``token_budget``.

    Whole sentences only; the single exception is an opening sentence longer than
    the budget itself, which is trimmed at a word boundary. Returns the lede text
    and the full sentences it was built from, so they are not repeated elsewhere.
    """
    kept: list[str] = []
    tokens = 0
    for sentence in sentences:
        cost = estimate_tokens(sentence)
        if tokens + cost > token_budget:
            if not kept:
                return _trim_to_tokens(sentence, token_budget), [sentence]
            break
        kept.append(sentence)
        tokens += cost
    return " ".join(kept), kept


def _trim_to_tokens(sentence: str, token_budget: int) -> str:
    """Cut ``sentence`` to the budget at a word boundary (lede-only exception)."""
    max_chars = token_budget * _CHARS_PER_TOKEN
    if len(sentence) <= max_chars:
        return sentence
    cut = sentence[:max_chars]
    if not sentence[max_chars].isspace() and " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip()


def _tokens(digest: dict[str, Any]) -> int:
    return estimate_tokens(build_state(digest))


def _with_meta(digest: dict[str, Any], chars: int) -> dict[str, Any]:
    """Attach ``meta`` with a self-consistent token count of the serialized digest.

    ``digest_tokens`` counts the whole serialized digest including ``meta`` itself,
    so the figure is refined until it stops moving (only its digit width can move
    it; the loop converges in one or two passes).
    """
    result = {**digest, "meta": {"language": "es", "chars": chars, "digest_tokens": 0}}
    tokens = _tokens(result)
    for _ in range(4):
        result["meta"]["digest_tokens"] = tokens
        refined = _tokens(result)
        if refined == tokens:
            return result
        tokens = refined
    result["meta"]["digest_tokens"] = tokens
    return result
