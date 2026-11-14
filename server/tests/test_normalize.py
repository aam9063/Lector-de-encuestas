"""Paste artifacts must not change the reading of a story.

Reproduced live: the same article, wrapped in markdown fences, classified as
``not_a_poll`` with p = 0.52 and the sheet went grey. The fence lines were part of the
state the model read.

The invariant that makes this safe: characters are replaced by spaces, never removed, so
every index still points at the same character of the text the user pasted.
"""

from ficha_tecnica.extractor.normalize import strip_paste_artifacts

STORY = (
    "SIMULACIÓN. Demoscopia Ficticia S.L. realizó 1.200 entrevistas entre el 3 y el 8 de "
    "noviembre con un margen de error de 2,8 puntos."
)


def test_a_fenced_block_loses_its_fences() -> None:
    fenced = f"```\n{STORY}\n```"

    cleaned = strip_paste_artifacts(fenced)

    assert "```" not in cleaned
    assert STORY in cleaned


def test_a_language_tag_is_removed_with_the_fence() -> None:
    cleaned = strip_paste_artifacts(f"```markdown\n{STORY}\n```")

    assert "markdown" not in cleaned
    assert STORY in cleaned


def test_the_length_never_changes() -> None:
    """Any change in length would move every evidence span the client relies on."""
    for text in (f"```\n{STORY}\n```", f"```text\n{STORY}\n```", STORY):
        assert len(strip_paste_artifacts(text)) == len(text)


def test_plain_text_is_returned_untouched() -> None:
    assert strip_paste_artifacts(STORY) is STORY or strip_paste_artifacts(STORY) == STORY


def test_inline_backticks_are_not_fences() -> None:
    text = "El codigo `npm test` aparece en la noticia."

    assert strip_paste_artifacts(text) == text


def test_indented_fences_are_cleaned_too() -> None:
    cleaned = strip_paste_artifacts(f"  ```\n{STORY}")

    assert "```" not in cleaned
