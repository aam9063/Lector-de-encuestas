"""ENC-09: the output sanitizer and its independent detector (section 7.5).

Two things are tested here, and they are deliberately built by different means:

- ``mask_vote_estimates`` removes any phrase that combines a formation with a figure.
  It works sentence by sentence, reusing the sentence splitter.
- ``find_leaks`` is an INDEPENDENT detector built on a character window and its own
  figure grammar, not on the sanitizer's sentence logic. A detector that shares the
  sanitizer's blind spot would report zero leaks while the app still leaked, so the
  detector is validated with positive controls before it is ever trusted.

The rule is absolute: no output text may carry a vote-estimate figure. It is always
active and has nothing to do with the blackout switch.
"""

import pytest

from ficha_tecnica.sanitizer import MASK, find_leaks, mask_vote_estimates

#: Text that MUST be detected: each one combines a formation with a figure. If the
#: detector misses any of these, every "zero leaks" assertion below is worthless.
LEAKS = [
    "El Partido Popular obtendría un 32 % de los votos.",
    "El PSOE lograría un 28,4 % según el sondeo.",
    "Vox sube hasta el 14 por ciento.",
    "Sumar obtendría 12 escaños.",
    "Según el estudio, el PP ganaría con el 34,2%.",
    "Podemos se quedaría con 3 diputados y un 2,1 %.",
    "Ciudadanos: 1,5 %.",
    "El BNG alcanzaría los 2 escaños en la provincia.",
]

#: Text that must NOT be touched: a figure with no formation is ordinary information.
CLEAN = [
    "El margen de error es de 2,8 puntos.",
    "La encuesta se hizo con 1.200 entrevistas.",
    "El nivel de confianza del 95 % se aplica a la muestra.",
    "Demoscopia Ficticia realizó 2.000 entrevistas.",
    "El trabajo de campo duró 6 días.",
]


@pytest.mark.parametrize("text", LEAKS)
def test_the_detector_catches_every_known_leak(text: str) -> None:
    """Positive control: a detector that never fires would pass every other test."""
    assert find_leaks(text), f"detector missed: {text}"


@pytest.mark.parametrize("text", CLEAN)
def test_the_detector_leaves_ordinary_information_alone(text: str) -> None:
    assert find_leaks(text) == []


@pytest.mark.parametrize("text", LEAKS)
def test_masking_removes_the_formation_and_the_figure(text: str) -> None:
    masked = mask_vote_estimates(text)

    assert MASK in masked
    assert find_leaks(masked) == []
    assert not any(party in masked for party in ("Partido Popular", "PSOE", "PP", "Vox"))


@pytest.mark.parametrize("text", LEAKS)
def test_no_output_can_pass_the_independent_detector(text: str) -> None:
    """The library's headline invariant: sanitized output never leaks."""
    assert find_leaks(mask_vote_estimates(text)) == []


@pytest.mark.parametrize("text", CLEAN)
def test_ordinary_information_survives_masking(text: str) -> None:
    assert mask_vote_estimates(text) == text


def test_masking_is_idempotent() -> None:
    once = mask_vote_estimates(LEAKS[0])

    assert mask_vote_estimates(once) == once


def test_mask_constant_is_the_documented_text() -> None:
    assert MASK == "[cifra de estimación omitida]"


def test_an_empty_text_is_not_a_crash() -> None:
    assert mask_vote_estimates("") == ""
    assert find_leaks("") == []


def test_the_sanitizer_never_calls_the_model() -> None:
    """Sanitizing is deterministic and local: it must not depend on Clef."""
    import ficha_tecnica.sanitizer.mask as mask_module

    with open(mask_module.__file__ or "", encoding="utf-8") as stream:
        source = stream.read()

    assert "clef_client" not in source
