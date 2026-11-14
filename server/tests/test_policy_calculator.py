"""M4 (margin coherence) and M5 (lead versus margin), section 7.3.

The document ships a worked table of theoretical margins; it is the acceptance reference
for the formula, so it is asserted row by row rather than trusted.
"""

from decimal import Decimal

import pytest

from ficha_tecnica.policy.calculator import (
    THEORETICAL_MARGINS,
    fired_rules,
    lead_ratio,
    lead_verdict,
    margin_is_implausible,
    theoretical_margin,
)
from ficha_tecnica.policy.config import PolicyConfig

POLICY = PolicyConfig()


@pytest.mark.parametrize(("sample_size", "expected"), sorted(THEORETICAL_MARGINS.items()))
def test_theoretical_margin_matches_the_documented_table(
    sample_size: int, expected: Decimal
) -> None:
    assert theoretical_margin(sample_size) == expected


def test_theoretical_margin_uses_z_2_for_95_5_percent() -> None:
    assert theoretical_margin(1200, confidence=Decimal("95.5")) == Decimal("2.9")


def test_a_bigger_sample_always_narrows_the_margin() -> None:
    margins = [theoretical_margin(n) for n in (400, 800, 1200, 2400, 3000)]

    assert margins == sorted(margins, reverse=True)


def test_a_zero_sample_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        theoretical_margin(0)


def test_a_margin_far_below_theoretical_is_implausible() -> None:
    """1,4 points for 1.200 interviews is half of the 2,8 the design allows."""
    assert margin_is_implausible(Decimal("1.4"), 1200, policy=POLICY) is True


def test_a_margin_above_theoretical_is_normal_not_flagged() -> None:
    """Design effects inflate margins; that is not a finding."""
    assert margin_is_implausible(Decimal("3.5"), 1200, policy=POLICY) is False


def test_the_90_percent_boundary_is_inclusive_on_the_safe_side() -> None:
    """2,8 theoretical x 0,90 = 2,52; exactly 2,52 is not below, so it does not fire."""
    assert margin_is_implausible(Decimal("2.52"), 1200, policy=POLICY) is False
    assert margin_is_implausible(Decimal("2.51"), 1200, policy=POLICY) is True


@pytest.mark.parametrize(
    ("lead", "margin", "expected"),
    [
        (Decimal("1.0"), Decimal("3.0"), Decimal("0.3")),
        (Decimal("2.0"), Decimal("3.0"), Decimal("0.7")),
        (Decimal("3.0"), Decimal("3.0"), Decimal("1.0")),
        (Decimal("4.0"), Decimal("3.0"), Decimal("1.3")),
        (Decimal("6.0"), Decimal("3.0"), Decimal("2.0")),
    ],
)
def test_lead_ratio_is_rounded_to_one_decimal(
    lead: Decimal, margin: Decimal, expected: Decimal
) -> None:
    assert lead_ratio(lead, margin) == expected


def test_a_zero_margin_cannot_produce_a_ratio() -> None:
    with pytest.raises(ValueError, match="positive"):
        lead_ratio(Decimal("3"), Decimal("0"))


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (Decimal("0.9"), "within_margin"),
        (Decimal("1.0"), "not_conclusive"),
        (Decimal("1.9"), "not_conclusive"),
        (Decimal("2.0"), "likely_real"),
        (Decimal("3.0"), "likely_real"),
    ],
)
def test_lead_verdict_boundaries(ratio: Decimal, expected: str) -> None:
    assert lead_verdict(ratio, POLICY) == expected


class TestFiredRules:
    """Which findings the arithmetic raises, never inventing what it cannot compute."""

    def test_nothing_fires_without_figures(self) -> None:
        fired = fired_rules(
            sample_size=None,
            declared_margin=None,
            lead=None,
            lead_decisive_probability=None,
            policy=POLICY,
        )

        assert fired == set()

    def test_m4_fires_on_an_implausible_margin(self) -> None:
        fired = fired_rules(
            sample_size=1200,
            declared_margin=Decimal("1.4"),
            lead=None,
            lead_decisive_probability=None,
            policy=POLICY,
        )

        assert fired == {"M4"}

    def test_m4_stays_silent_on_a_plausible_margin(self) -> None:
        fired = fired_rules(
            sample_size=1200,
            declared_margin=Decimal("2.8"),
            lead=None,
            lead_decisive_probability=None,
            policy=POLICY,
        )

        assert "M4" not in fired

    def test_m5_fires_when_a_decisive_lead_is_within_the_margin(self) -> None:
        fired = fired_rules(
            sample_size=1200,
            declared_margin=Decimal("2.8"),
            lead=Decimal("2"),
            lead_decisive_probability=0.95,
            policy=POLICY,
        )

        assert "M5" in fired

    def test_m5_stays_silent_when_the_headline_is_not_decisive(self) -> None:
        """The arithmetic is suspicious, but nobody claimed a winner: no finding."""
        fired = fired_rules(
            sample_size=1200,
            declared_margin=Decimal("2.8"),
            lead=Decimal("2"),
            lead_decisive_probability=0.30,
            policy=POLICY,
        )

        assert "M5" not in fired

    def test_m5_stays_silent_when_the_lead_exceeds_twice_the_margin(self) -> None:
        fired = fired_rules(
            sample_size=1200,
            declared_margin=Decimal("2.8"),
            lead=Decimal("6"),
            lead_decisive_probability=0.99,
            policy=POLICY,
        )

        assert "M5" not in fired


def test_m4_and_m5_can_fire_together() -> None:
    fired = fired_rules(
        sample_size=1200,
        declared_margin=Decimal("1.4"),
        lead=Decimal("1"),
        lead_decisive_probability=0.99,
        policy=POLICY,
    )

    assert fired == {"M4", "M5"}


def test_the_arithmetic_never_needs_clef() -> None:
    """Both rules are pure arithmetic: the module must not import the client."""
    import ficha_tecnica.policy.calculator as calculator

    source = calculator.__file__ or ""
    with open(source, encoding="utf-8") as stream:
        text = stream.read()

    assert "clef_client" not in text
