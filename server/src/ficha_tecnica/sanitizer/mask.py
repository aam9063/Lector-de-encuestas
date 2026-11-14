"""Output sanitizer: no output text may carry a vote-estimate figure (section 7.5).

The rule is absolute and independent of the blackout switch: whenever an output phrase
combines a formation with a figure, the whole phrase is replaced by ``MASK``. The mask
drops the formation name too, because section 10 forbids naming a party in a finding and
because keeping the name while hiding the number would still signal who is ahead.

Sentences without a formation are ordinary information ("a margin of 2.8 points") and are
left untouched: over-masking technical data would make the sheet useless.

The detector that proves this works lives in ``detector.py`` and is built differently on
purpose; see its docstring.
"""

import re

from ficha_tecnica.extractor.candidates import split_sentences
from ficha_tecnica.extractor.entities import find_entities

MASK = "[cifra de estimación omitida]"

_DIGIT = re.compile(r"\d")


def mask_vote_estimates(text: str) -> str:
    """Replace every phrase that combines a formation with a figure.

    Everything else is copied verbatim, so a caller that maps spans back to its own input
    keeps working.
    """
    if not text:
        return text
    party_spans = [span for span in find_entities(text) if span.kind == "party"]
    if not party_spans:
        return text

    replacements: list[tuple[int, int]] = []
    for sentence in split_sentences(text):
        phrase = text[sentence.start : sentence.end]
        names_party = any(
            sentence.start <= span.start and span.end <= sentence.end for span in party_spans
        )
        if names_party and _DIGIT.search(phrase):
            replacements.append((sentence.start, sentence.end))

    if not replacements:
        return text

    parts: list[str] = []
    cursor = 0
    for start, end in replacements:
        parts.append(text[cursor:start])
        parts.append(MASK)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)
