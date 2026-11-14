"""Curated entity spans and voting-estimate spans (ENC-04 tasks T1 and T2)."""

import itertools

import pytest

from ficha_tecnica.extractor.entities import (
    find_entities,
    find_estimates,
    load_parties,
    load_pollsters,
)


def _entity_slices(text: str) -> list[str]:
    return [text[span.start : span.end] for span in find_entities(text)]


def test_finds_pollster_variant_with_exact_span() -> None:
    text = "Según GAD3, el sondeo es claro."
    spans = find_entities(text)
    assert len(spans) == 1
    span = spans[0]
    assert span.kind == "pollster"
    assert span.name == "GAD3"
    assert span.variant == "GAD3"
    assert text[span.start : span.end] == "GAD3"
    assert span.start == text.index("GAD3")


def test_matches_are_case_insensitive() -> None:
    text = "psoe y Ciudadanos en la misma frase"
    spans = find_entities(text)
    assert {span.name for span in spans} == {"PSOE", "Ciudadanos"}
    assert text[spans[0].start : spans[0].end] == "psoe"


def test_word_boundaries_reject_substring_hits() -> None:
    text = "La firma APP, el partido PPSOE, pero sí el PP y el PSOE."
    assert _entity_slices(text) == ["PP", "PSOE"]


def test_accents_do_not_block_matching() -> None:
    plain = "La casa Simple Logica publicó el sondeo."
    spans = find_entities(plain)
    assert len(spans) == 1
    assert spans[0].name == "Simple Lógica"
    assert plain[spans[0].start : spans[0].end] == "Simple Logica"

    accented = "La casa SIMPLE LÓGICA publicó el sondeo."
    assert len(find_entities(accented)) == 1


def test_longest_variant_wins() -> None:
    text = "El CIS y el Centro de Investigaciones Sociológicas coinciden."
    spans = find_entities(text)
    full = next(span for span in spans if span.start == text.index("Centro"))
    assert full.variant == "Centro de Investigaciones Sociológicas"
    assert text[full.start : full.end] == "Centro de Investigaciones Sociológicas"


def test_overlapping_variants_collapse_into_one_span() -> None:
    text = "Vota a Junts per Catalunya."
    spans = find_entities(text)
    assert len(spans) == 1
    assert spans[0].variant == "Junts per Catalunya"


def test_spans_are_ordered_and_non_overlapping() -> None:
    text = "El CIS, GAD3 y Sigma Dos coinciden con el PSOE y Vox."
    spans = find_entities(text)
    assert len(spans) == 5
    assert all(a.end <= b.start for a, b in itertools.pairwise(spans))


def test_loaders_expose_the_curated_lists() -> None:
    pollsters = load_pollsters()
    parties = load_parties()
    assert pollsters and parties
    assert len({entry.name for entry in pollsters}) == len(pollsters)
    assert len({entry.name for entry in parties}) == len(parties)
    for entry in (*pollsters, *parties):
        assert entry.variants
        assert all(variant.strip() for variant in entry.variants)


@pytest.mark.parametrize("entry", load_parties(), ids=[entry.name for entry in load_parties()])
def test_every_party_is_found_identically(entry) -> None:
    text = f"Menciona {entry.name} en el titular."
    spans = find_entities(text)
    assert spans, entry.name
    for span in spans:
        assert span.name == entry.name
        assert span.kind == "party"
        assert text[span.start : span.end] in entry.variants
    assert all(a.end <= b.start for a, b in itertools.pairwise(spans))


@pytest.mark.parametrize("entry", load_pollsters(), ids=[entry.name for entry in load_pollsters()])
def test_every_pollster_is_found_identically(entry) -> None:
    text = f"Menciona {entry.name} en el titular."
    spans = find_entities(text)
    assert spans, entry.name
    for span in spans:
        assert span.name == entry.name
        assert span.kind == "pollster"
        assert text[span.start : span.end] in entry.variants
    assert all(a.end <= b.start for a, b in itertools.pairwise(spans))


def test_vote_percentage_span() -> None:
    text = "El Partido Popular obtendría un 32 % de los votos."
    spans = find_estimates(text)
    assert len(spans) == 1
    assert spans[0].kind == "figure"
    assert text[spans[0].start : spans[0].end] == "32 %"


def test_seats_span() -> None:
    text = "Podemos alcanzaría 20 escaños según el sondeo."
    spans = find_estimates(text)
    assert len(spans) == 1
    assert spans[0].kind == "seats"
    assert text[spans[0].start : spans[0].end] == "20 escaños"


def test_no_estimate_without_figure() -> None:
    assert find_estimates("El Partido Popular ganó las elecciones.") == []


def test_no_estimate_without_party() -> None:
    assert find_estimates("Un 32 % aprueba la gestión del Gobierno.") == []


def test_pollster_alone_does_not_trigger_estimate() -> None:
    assert find_estimates("El CIS publicó un 32 % de aprobación.") == []


def test_no_estimate_across_sentences() -> None:
    assert find_estimates("El PP ganó las elecciones. Un 32 % apoyó la medida.") == []


def test_several_parties_several_figures() -> None:
    text = "El PSOE obtendría un 32 % y el PP se quedaría en un 25 %."
    spans = find_estimates(text)
    assert [text[span.start : span.end] for span in spans] == ["32 %", "25 %"]
