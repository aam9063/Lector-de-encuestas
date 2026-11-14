"""Sentence splitting with original-text positions and per-item candidates (ENC-04 T3/T4)."""

import itertools
from pathlib import Path

import pytest
import yaml

from ficha_tecnica.extractor.candidates import (
    SentenceSpan,
    all_candidates,
    candidates_for,
    checklist_item_ids,
    split_sentences,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# One line on purpose: sentence positions are indices into the ORIGINAL text, and a
# wrapped triple-quoted string would insert newlines into it.
NEWS = (
    "MADRID, 10 de noviembre. La encuesta de GAD3 para EL MUNDO se realizó entre el 3 y el 9 "
    "de noviembre con 1.200 personas entrevistadas telefónicamente. El margen de error es de "
    "±2,8 puntos, para un nivel de confianza del 95 %. Según los datos, el PSOE obtendría un "
    "32 % de los votos y el PP se quedaría en un 25 %."
)

EXPECTED_SENTENCES = [
    "MADRID, 10 de noviembre.",
    "La encuesta de GAD3 para EL MUNDO se realizó entre el 3 y el 9 de noviembre con 1.200 "
    "personas entrevistadas telefónicamente.",
    "El margen de error es de ±2,8 puntos, para un nivel de confianza del 95 %.",
    "Según los datos, el PSOE obtendría un 32 % de los votos y el PP se quedaría en un 25 %.",
]

P0_ITEMS = ("a_sample_size", "a_margin", "a_fieldwork_dates", "a_entity")

EXPECTED_BY_ITEM = {
    "a_sample_size": EXPECTED_SENTENCES[1],
    "a_margin": EXPECTED_SENTENCES[2],
    "a_fieldwork_dates": EXPECTED_SENTENCES[1],
    "a_entity": EXPECTED_SENTENCES[1],
}


def test_sentences_reproduce_the_original_text() -> None:
    spans = split_sentences(NEWS)
    assert [NEWS[span.start : span.end] for span in spans] == EXPECTED_SENTENCES


def test_numbers_are_not_split_into_two_sentences() -> None:
    text = "La muestra fue de 1.200 personas y el error de 2,8 puntos."
    assert [text[span.start : span.end] for span in split_sentences(text)] == [text]


def test_question_exclamation_and_newline_breaks() -> None:
    text = "¿Quién ganará? ¡El PP! Y la suma da 57 %.\nY aquí otra línea."
    spans = split_sentences(text)
    assert [text[span.start : span.end] for span in spans] == [
        "¿Quién ganará?",
        "¡El PP!",
        "Y la suma da 57 %.",
        "Y aquí otra línea.",
    ]


def test_empty_text_has_no_sentences() -> None:
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_spans_are_ordered_and_disjoint() -> None:
    spans = split_sentences(NEWS)
    assert all(a.end <= b.start for a, b in itertools.pairwise(spans))


@pytest.mark.parametrize(("item_id", "expected"), list(EXPECTED_BY_ITEM.items()))
def test_p0_items_find_their_sentences(item_id: str, expected: str) -> None:
    found = candidates_for(NEWS, item_id)
    assert found, item_id
    assert all(isinstance(span, SentenceSpan) for span in found)
    slices = [NEWS[span.start : span.end] for span in found]
    assert expected in slices, (item_id, slices)


def test_item_without_matching_cues_returns_empty() -> None:
    assert candidates_for(NEWS, "a_weighting") == []
    assert candidates_for(NEWS, "a_nonresponse") == []
    assert candidates_for(NEWS, "a_external_sheet") == []


def test_unknown_item_id_raises() -> None:
    with pytest.raises(ValueError, match="unknown checklist item"):
        candidates_for(NEWS, "a_made_up_item")


def test_all_candidates_covers_the_live_checklist() -> None:
    with (REPO_ROOT / "config" / "checklist.v1.yaml").open(encoding="utf-8") as stream:
        checklist = yaml.safe_load(stream)
    ids = {item["id"] for item in checklist["items"]}
    assert set(checklist_item_ids()) == ids

    result = all_candidates(NEWS)
    assert set(result) == ids
    for item_id in P0_ITEMS:
        assert result[item_id], item_id


def test_every_candidate_slice_reproduces_its_sentence() -> None:
    for spans in all_candidates(NEWS).values():
        for span in spans:
            assert NEWS[span.start : span.end] in EXPECTED_SENTENCES
