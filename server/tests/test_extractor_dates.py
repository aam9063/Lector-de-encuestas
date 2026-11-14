"""Fieldwork date ranges in Spanish, including abbreviations and month crossings."""

from datetime import date

import pytest

from ficha_tecnica.extractor.dates import parse_date, parse_date_range

YEAR = 2026


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("del 3 al 9 de noviembre", (date(2026, 11, 3), date(2026, 11, 9))),
        ("entre el 3 y el 9 de noviembre", (date(2026, 11, 3), date(2026, 11, 9))),
        ("del 3 al 9 de nov.", (date(2026, 11, 3), date(2026, 11, 9))),
        ("3 y 4 de noviembre", (date(2026, 11, 3), date(2026, 11, 4))),
        ("del 30 de octubre al 2 de noviembre", (date(2026, 10, 30), date(2026, 11, 2))),
        ("desde el 1 hasta el 5 de septiembre", (date(2026, 9, 1), date(2026, 9, 5))),
        ("trabajo de campo: 3-9 de noviembre", (date(2026, 11, 3), date(2026, 11, 9))),
    ],
)
def test_parses_a_date_range(raw: str, expected: tuple[date, date]) -> None:
    assert parse_date_range(raw, YEAR) == expected


def test_crosses_the_year_boundary_when_the_end_month_is_earlier() -> None:
    result = parse_date_range("del 28 de diciembre al 3 de enero", YEAR)

    assert result is not None
    start, end = result
    assert start == date(2026, 12, 28)
    assert end == date(2027, 1, 3)


def test_returns_none_without_a_range() -> None:
    assert parse_date_range("no hay fechas aqui", YEAR) is None


def test_range_with_reversed_days_is_not_a_range() -> None:
    assert parse_date_range("del 9 al 3 de noviembre", YEAR) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9 de noviembre", date(2026, 11, 9)),
        ("9 de nov.", date(2026, 11, 9)),
        ("9 de noviembre de 2025", date(2025, 11, 9)),
    ],
)
def test_parses_a_single_date(raw: str, expected: date) -> None:
    assert parse_date(raw, YEAR) == expected


def test_unknown_month_is_not_a_date() -> None:
    assert parse_date("9 de noviembreish", YEAR) is None
