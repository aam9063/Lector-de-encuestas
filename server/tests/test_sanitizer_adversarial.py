"""Adversarial corpus for the sanitizer.

The rule from section 7.5 is "zero leaks in the whole evaluation suite", so before the
evaluation exists this file attacks the sanitizer from every angle the press uses to state
a poll result. It also proves the sanitizer is selective: masking must remove the poll
result without eating the technical data around it.
"""

import pytest

from ficha_tecnica.sanitizer import MASK, find_leaks, mask_vote_estimates

#: Each text states a poll result and MUST come out of the sanitizer clean.
RESULTS_THAT_MUST_BE_MASKED = [
    "El PP obtendría un 34,2 % de los votos.",
    "Un 32 % de los votos iría al PSOE.",
    "PARTIDO POPULAR: 34,2%",
    "El partido popular obtendria un 34 por ciento.",
    "Vox y Sumar sumarían 20 escaños entre los dos.",
    "Según el sondeo, el PP lograría 12 diputados.",
    "El BNG: 2,1 %.",
    "Más País obtendría 3 actas.",
    "El PSOE baja al 28,4 %\ny el PP sube al 34,2 %.",
    "Sumar se queda con 8 y el PP con 137.",
    "Ciudadanos desaparece: 0,4 %.",
    "ERC obtendría 7 escaños, Junts 6 y el PNV 5.",
]


@pytest.mark.parametrize("text", RESULTS_THAT_MUST_BE_MASKED)
def test_a_stated_poll_result_never_survives(text: str) -> None:
    masked = mask_vote_estimates(text)

    assert find_leaks(masked) == [], f"leaked: {masked!r}"
    assert MASK in masked


@pytest.mark.parametrize("text", RESULTS_THAT_MUST_BE_MASKED)
def test_the_original_text_does_leak_before_masking(text: str) -> None:
    """Control: if the detector cannot see the leak unmasked, the previous test is void."""
    assert find_leaks(text), f"detector is blind to: {text!r}"


def test_masking_is_selective_and_keeps_the_technical_data() -> None:
    text = (
        "La encuesta se hizo con 1.200 entrevistas. "
        "El PP obtendría un 34 % de los votos. "
        "El margen de error es de 2,8 puntos."
    )

    masked = mask_vote_estimates(text)

    assert "1.200 entrevistas" in masked
    assert "2,8 puntos" in masked
    assert "34 %" not in masked
    assert "PP" not in masked
    assert find_leaks(masked) == []


def test_a_long_story_only_loses_the_result_sentences() -> None:
    text = (
        "SIMULACIÓN. Demoscopia Ficticia realizó 2.000 entrevistas entre el 3 y el 9 de "
        "noviembre con un margen de 2,2 puntos. El PP ganaría con el 34,2 % y el PSOE "
        "caería al 28,4 %. El nivel de confianza es del 95 %."
    )

    masked = mask_vote_estimates(text)

    assert "2.000 entrevistas" in masked
    assert "2,2 puntos" in masked
    assert "95 %" in masked
    assert "34,2" not in masked
    assert "28,4" not in masked
    assert find_leaks(masked) == []


def test_masking_twice_changes_nothing() -> None:
    once = mask_vote_estimates(RESULTS_THAT_MUST_BE_MASKED[0])

    assert mask_vote_estimates(once) == once


def test_a_text_without_formations_is_returned_unchanged() -> None:
    text = "Demoscopia Ficticia realizó 1.200 entrevistas con un margen de 2,8 puntos."

    assert mask_vote_estimates(text) == text
    assert find_leaks(text) == []


def test_known_limitation_a_figure_split_into_the_next_sentence_is_not_masked() -> None:
    """Documented gap, not an accepted leak in production.

    The sanitizer works phrase by phrase, so a party in one sentence and the figure in the
    next survives. It is bounded on purpose: output messages are fixed templates that never
    carry figures at all, and the sheet expresses arithmetic as ratios. Widening the window
    here would mask unrelated sentences and blind the reader.
    """
    text = "Según el sondeo, el PP ganaría. Obtendría el 32 % de los votos."

    assert mask_vote_estimates(text) == text
    assert find_leaks(text) == []


def test_known_over_masking_ciudadanos_is_also_a_common_noun() -> None:
    """Fail-closed cost, documented on purpose.

    "Ciudadanos" is both a party and an ordinary word, so a sentence about public opinion
    loses its figure. That is the direction the design asks for: a lost figure costs a
    masked sentence, a leaked figure costs the project. Tightening it needs a capitalised
    heuristic, which would then miss lower-case press copy.
    """
    text = "El 60 % de los ciudadanos cree que la situacion empeorara."

    masked = mask_vote_estimates(text)

    assert masked == MASK
    assert find_leaks(masked) == []
