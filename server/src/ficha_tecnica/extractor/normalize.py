"""Paste artifacts: what arrives when someone copies from a chat or a web page.

A printed block usually brings its markdown fences, sometimes a bare ``` line, and the
copy can bring a leading language tag. Those bytes are not part of the story, but they sit
in the state the model reads: with a fence around the text, an obvious poll classified as
``not_a_poll`` with p = 0.52 and the sheet came back grey.

Everything here REPLACES characters with spaces instead of deleting them, so the length of
the text never changes. That is what keeps the evidence spans valid: the client highlights
on the text it pasted, and every index the pipeline returns still points at the same
character.
"""

import re

#: A fence marker and its optional language tag, wherever it appears. Matching the marker
#: only, and not the whole line, is what makes a fence glued to the text safe: blanking the
#: line instead deleted the entire story and left an empty state, which the model read as
#: "not a poll".
_FENCE = re.compile(r"```(?:markdown|md|text|txt|plaintext|html|json)?", re.IGNORECASE)


def strip_paste_artifacts(text: str) -> str:
    """Blank out markdown fences without moving any character."""
    if "```" not in text:
        return text
    return _FENCE.sub(lambda match: " " * len(match.group(0)), text)
