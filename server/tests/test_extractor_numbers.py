"""Spanish number formats: 1.200 is one thousand two hundred, 2,8 is two point eight."""

from decimal import Decimal

import pytest

from ficha_tecnica.extractor.numbers import parse_percentage, parse_spanish_number


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.200", Decimal("1200")),
        ("1200", Decimal("1200")),
        ("12.345", Decimal("12345")),
        ("1.234.567", Decimal("1234567")),
        ("2,8", Decimal("2.8")),
        ("1.200,5", Decimal("1200.5")),
        ("0,5", Decimal("0.5")),
        ("95", Decimal("95")),
        ("  1.200  ", Decimal("1200")),
    ],
)
def test_parses_spanish_numbers(raw: str, expected: Decimal) -> None:
    assert parse_spanish_number(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1.20", "1,2,3", "2,8 %", "-"])
def test_rejects_values_that_are_not_a_single_number(raw: str) -> None:
    assert parse_spanish_number(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2,8 %", Decimal("2.8")),
        ("2,8%", Decimal("2.8")),
        ("±2,8", Decimal("2.8")),
        ("± 2,8 %", Decimal("2.8")),
        ("95 %", Decimal("95")),
        ("95,5 %", Decimal("95.5")),
        ("3 puntos", Decimal("3")),
        ("un 12 %", Decimal("12")),
    ],
)
def test_finds_a_percentage_anywhere_in_sentences(raw: str, expected: Decimal) -> None:
    assert parse_percentage(raw) == expected


def test_returns_none_when_there_is_no_percentage() -> None:
    assert parse_percentage("no hay cifras aqui") is None
