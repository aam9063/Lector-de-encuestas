"""Pulling the numbers the policy needs: sample size, margin and confidence.

Each extractor requires a cue next to the figure so a party's vote share is never
mistaken for a sample size or a margin.
"""

from decimal import Decimal

import pytest

from ficha_tecnica.extractor.metrics import (
    extract_confidence,
    extract_margin,
    extract_sample_size,
)

NEWS = (
    "SIMULACION. Demoscopia Ficticia S.L. realizo una encuesta con 1.200 entrevistas "
    "entre el 3 y el 9 de noviembre. El margen de error es de 2,8 puntos. "
    "El Partido Azul obtendria un 32 % de los votos."
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("la muestra fue de 1.200 personas", 1200),
        ("n = 1.200", 1200),
        ("n=1200", 1200),
        ("se realizaron 2.000 entrevistas", 2000),
        ("un total de 1.500 encuestados", 1500),
        ("encuesta a 800 personas", 800),
        ("1.200 entrevistas", 1200),
    ],
)
def test_finds_the_sample_size(text: str, expected: int) -> None:
    assert extract_sample_size(text) == expected


def test_a_vote_share_is_not_a_sample_size() -> None:
    assert extract_sample_size("El Partido Azul obtendria un 32 % de los votos") is None


def test_finds_the_sample_size_in_a_whole_news_story() -> None:
    assert extract_sample_size(NEWS) == 1200


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("margen de error de 2,8 puntos", Decimal("2.8")),
        ("margen de error del ±3 %", Decimal("3")),
        ("error muestral de 4 puntos", Decimal("4")),
        ("con un margen de ± 2,5", Decimal("2.5")),
        ("+-2,8 puntos", Decimal("2.8")),
    ],
)
def test_finds_the_declared_margin(text: str, expected: Decimal) -> None:
    assert extract_margin(text) == expected


def test_a_vote_share_is_not_a_margin() -> None:
    assert extract_margin("El Partido Azul obtendria un 32 % de los votos") is None


def test_finds_the_margin_in_a_whole_news_story() -> None:
    assert extract_margin(NEWS) == Decimal("2.8")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("nivel de confianza del 95 %", Decimal("95")),
        ("para un nivel de confianza del 95,5 %", Decimal("95.5")),
        ("margen del 3 % con una confianza del 99 %", Decimal("99")),
    ],
)
def test_finds_the_confidence_level(text: str, expected: Decimal) -> None:
    assert extract_confidence(text) == expected


def test_a_plain_percentage_is_not_a_confidence_level() -> None:
    assert extract_confidence("El Partido Azul obtendria un 95 % de los votos") is None


def test_a_margin_written_as_a_plain_percentage_is_read() -> None:
    """Found on a real article: "con un margen de error del 0,5%" returned None.

    The pattern ended with a word boundary after the optional "%", and between "%" and a
    space there is no boundary, so every margin written without a "±" was invisible.
    """
    for texto, esperado in (
        ("con un margen de error del 0,5% para el conjunto de la muestra", Decimal("0.5")),
        ("un margen de error de 2,8 % al 95 % de confianza", Decimal("2.8")),
        ("margen de error del 3%", Decimal("3")),
    ):
        assert extract_margin(texto) == esperado, texto
