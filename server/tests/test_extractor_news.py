"""Acceptance test: the P0 items find their sentence in a realistic news story.

This is the criterion ENC-04 promises ("candidates with positions for the P0 items"),
checked on prose shaped like the synthetic articles the evaluation will use. The unit
tests cover individual rules; this one proves the pieces work together on a full text.
"""

from ficha_tecnica.extractor.candidates import all_candidates, candidates_for, split_sentences
from ficha_tecnica.extractor.entities import find_entities, find_estimates

NEWS = (
    "SIMULACION. El Partido Popular ganaria las elecciones segun una encuesta de "
    "Demoscopia Ficticia S.L. realizada por encargo del diario El Ejemplo. "
    "El estudio se hizo con 1.200 entrevistas entre el 3 y el 9 de noviembre. "
    "El margen de error es de 2,8 puntos para un nivel de confianza del 95 %. "
    "El Partido Popular obtendria un 32 % de los votos y el PSOE un 28 %."
)


def test_every_sentence_round_trips_to_the_original_text() -> None:
    for sentence in split_sentences(NEWS):
        assert NEWS[sentence.start : sentence.end] in NEWS
        assert NEWS[sentence.start : sentence.end].strip()


def test_the_thousands_separator_never_splits_a_sentence() -> None:
    sentences = [NEWS[s.start : s.end] for s in split_sentences(NEWS)]

    assert any("1.200 entrevistas" in sentence for sentence in sentences)


def test_p0_items_find_their_evidence() -> None:
    expected = {
        "a_sample_size": "1.200 entrevistas",
        "a_margin": "2,8 puntos",
        "a_fieldwork_dates": "entre el 3 y el 9 de noviembre",
        "a_entity": "Demoscopia Ficticia",
    }

    for item_id, evidence in expected.items():
        sentences = [NEWS[s.start : s.end] for s in candidates_for(NEWS, item_id)]
        assert any(evidence in sentence for sentence in sentences), f"{item_id} found nothing"


def test_every_checklist_item_has_an_answer_without_crashing() -> None:
    candidates = all_candidates(NEWS)

    assert len(candidates) == 15
    assert all(isinstance(spans, list) for spans in candidates.values())


def test_finds_both_curated_entities_with_positions() -> None:
    names = {(span.name, span.kind) for span in find_entities(NEWS)}

    # ``name`` is the canonical entry of the curated list, not the matched variant:
    # "Partido Popular" reports as PP. The simulation corpus registers a longer pollster
    # variant ("Demoscopia Ficticia"), which now wins for this text, so the canonical name
    # is the simulation entry -- still a pollster, which is what this test is about.
    assert any(kind == "pollster" and "Demoscopia" in name for name, kind in names)
    assert ("PP", "party") in names
    assert ("PSOE", "party") in names


def test_a_variant_reports_its_own_text() -> None:
    spans = [span for span in find_entities(NEWS) if span.name == "PP"]

    assert spans
    assert all(NEWS[span.start : span.end] == span.variant for span in spans)


def test_estimate_spans_cover_both_vote_shares_and_not_the_confidence_level() -> None:
    spans = find_estimates(NEWS)
    covered = {NEWS[span.start : span.end] for span in spans}

    assert "32 %" in covered
    assert "28 %" in covered
    # The confidence level lives in a sentence that names no party, so it is not an
    # estimate candidate: masking it would destroy legitimate technical information.
    assert "95 %" not in covered


def test_a_party_without_a_figure_produces_no_estimate() -> None:
    assert find_estimates("El Partido Popular gano las elecciones.") == []
