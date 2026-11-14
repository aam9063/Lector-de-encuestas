"""Adversarial limits for the bounded digests.

The unit tests prove the shape; these prove the ceiling holds under abuse: a text far
larger than any real story, an empty input, a text with no figures at all, and the one
case that must never happen — a vote-estimate figure being masked before Clef sees it.
"""

import json

import pytest

from ficha_tecnica.extractor.digest import (
    build_digest_a,
    build_digest_b,
    build_digest_c,
    build_state,
    estimate_tokens,
)

BUDGETS = {"a": 1200, "b": 500, "c": 400}


def _sentences(count: int, template: str) -> str:
    return " ".join(template.format(index=index) for index in range(count))


def test_budgets_hold_for_a_very_large_text() -> None:
    news = _sentences(
        400,
        "La encuesta numero {index} se hizo con 1.200 entrevistas y un margen de error "
        "de 2,8 puntos para un nivel de confianza del 95 %.",
    )
    assert len(news) > 40_000

    digests = {"a": build_digest_a(news), "b": build_digest_b(news), "c": build_digest_c(news)}

    for name, digest in digests.items():
        tokens = estimate_tokens(build_state(digest))
        assert tokens <= BUDGETS[name], f"digest {name} exceeded its budget: {tokens}"


def test_meta_reports_the_real_character_count() -> None:
    news = "SIMULACION. Encuesta con 1.200 entrevistas. Margen de error de 2,8 puntos."

    digest = build_digest_a(news)

    assert digest["meta"]["chars"] == len(news)
    assert digest["meta"]["language"] == "es"
    assert digest["meta"]["digest_tokens"] == estimate_tokens(build_state(digest))


def test_empty_input_produces_empty_digests_without_raising() -> None:
    for digest, key in (
        (build_digest_a(""), "technical_sentences"),
        (build_digest_b(""), "figure_sentences"),
        (build_digest_c(""), "quoted_questions"),
    ):
        assert digest[key] == []
        assert digest["meta"]["chars"] == 0


def test_a_text_without_figures_yields_no_figure_sentences() -> None:
    news = "SIMULACION. El Partido Azul gano las elecciones segun los sondeos."

    assert build_digest_b(news)["figure_sentences"] == []


def test_a_vote_estimate_reaches_clef_unmasked() -> None:
    """Digest B is input, not output: masking here would hide the figure under review."""
    news = (
        "SIMULACION. Segun Demoscopia, el Partido Popular obtendria un 34,2 % de los "
        "sufragios frente al 30,1 % del PSOE. El margen de error es de 2,8 puntos."
    )

    digest = build_digest_b(news)
    # The opening sentence lands in the lede, later figure sentences in their own list;
    # the invariant is about the whole input digest, not about which field holds it.
    whole = " ".join([digest["headline"], digest["lede"], *digest["figure_sentences"]])

    assert "34,2 %" in whole
    assert "cifra de estimacion omitida" not in whole


def test_a_quoted_question_inside_a_longer_sentence_is_still_found() -> None:
    news = (
        "SIMULACION. El cuestionario incluyo la pregunta "
        "«¿Votaria usted de nuevo al mismo partido que en 2023?» y otras tres."
    )

    assert build_digest_c(news)["quoted_questions"] == [
        "¿Votaria usted de nuevo al mismo partido que en 2023?"
    ]


def test_figure_sentences_are_capped_at_six() -> None:
    news = _sentences(
        30,
        "El Partido Azul sube {index} puntos y el Partido Rojo baja 2 puntos.",
    )

    assert len(build_digest_b(news)["figure_sentences"]) == 6


@pytest.mark.parametrize("digest_fn", [build_digest_a, build_digest_b, build_digest_c])
def test_state_is_compact_json_that_round_trips(digest_fn) -> None:
    news = "SIMULACION. Encuesta con 1.200 entrevistas entre el 3 y el 9 de noviembre."

    state = build_state(digest_fn(news))

    assert isinstance(state, str)
    assert ", " not in state and '": ' not in state
    assert json.loads(state) == digest_fn(news)
