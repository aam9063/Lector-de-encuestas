"""Margin coherence (M4) and lead versus margin (M5), section 7.3.

Both rules are pure arithmetic on figures the extractor already found, so they live in
code and never in Clef. All values are ``Decimal``: a float rounding error here would
move a finding across a threshold.

M4 warns, it does not accuse: a declared margin smaller than 90 % of the theoretical
one for simple random sampling may simply mean a different design. A declared margin
larger than theoretical is normal (design effects) and is never flagged.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

from ficha_tecnica.policy.config import PolicyConfig

Z_95 = Decimal("1.96")
Z_95_5 = Decimal("2.00")
_ONE_DECIMAL = Decimal("0.1")
_MAX_PROBABILITY = Decimal("0.25")  # p = 0.5 gives the widest possible margin

LeadVerdict = Literal["within_margin", "not_conclusive", "likely_real"]

#: The worked table of section 7.3, kept as the acceptance reference for the formula.
THEORETICAL_MARGINS: dict[int, Decimal] = {
    400: Decimal("4.9"),
    600: Decimal("4.0"),
    800: Decimal("3.5"),
    1000: Decimal("3.1"),
    1200: Decimal("2.8"),
    1500: Decimal("2.5"),
    2000: Decimal("2.2"),
    2400: Decimal("2.0"),
    3000: Decimal("1.8"),
}


def theoretical_margin(sample_size: int, *, confidence: Decimal | None = None) -> Decimal:
    """Maximum margin in points for simple random sampling at 95 % (or 95,5 %).

    ``e = z * sqrt(0.25 / n)``, rounded to one decimal like the document's table.
    """
    if sample_size <= 0:
        raise ValueError("sample size must be positive")
    z = Z_95_5 if confidence is not None and confidence == Decimal("95.5") else Z_95
    margin = z * (_MAX_PROBABILITY / Decimal(sample_size)).sqrt()
    return (margin * 100).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP)


def margin_is_implausible(
    declared_margin: Decimal,
    sample_size: int,
    *,
    confidence: Decimal | None = None,
    policy: PolicyConfig,
) -> bool:
    """True when the declared margin is suspiciously small for that sample (M4)."""
    theoretical = theoretical_margin(sample_size, confidence=confidence)
    return declared_margin < theoretical * policy.declared_below_theoretical_ratio


def lead_ratio(lead: Decimal, declared_margin: Decimal) -> Decimal:
    """``r = lead / margin``; the only figure the output is allowed to carry."""
    if declared_margin <= 0:
        raise ValueError("declared margin must be positive")
    return (lead / declared_margin).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP)


def lead_verdict(ratio: Decimal, policy: PolicyConfig) -> LeadVerdict:
    """Classify ``r`` into the three readings of section 7.3."""
    if ratio < policy.lead_ratio_within_margin:
        return "within_margin"
    if ratio < policy.lead_ratio_aapor_min:
        return "not_conclusive"
    return "likely_real"


def fired_rules(
    *,
    sample_size: int | None,
    declared_margin: Decimal | None,
    lead: Decimal | None,
    lead_decisive_probability: float | None,
    confidence: Decimal | None = None,
    policy: PolicyConfig,
) -> set[str]:
    """Which arithmetic findings fire (M4, M5), with what is actually known."""
    fired: set[str] = set()

    if (
        sample_size is not None
        and declared_margin is not None
        and margin_is_implausible(
            declared_margin, sample_size, confidence=confidence, policy=policy
        )
    ):
        fired.add("M4")

    if declared_margin is not None and lead is not None:
        ratio = lead_ratio(lead, declared_margin)
        fires_m5 = (
            ratio < policy.lead_ratio_aapor_min
            and lead_decisive_probability is not None
            and Decimal(str(lead_decisive_probability)) >= policy.lead_decisive_flag_min_p
        )
        if fires_m5:
            fired.add("M5")

    return fired


def parse_figure(value: str) -> Decimal:
    """Parse a figure coming from the extractor, refusing anything ambiguous."""
    try:
        return Decimal(value.strip())
    except InvalidOperation as error:  # pragma: no cover - caller always passes a figure
        raise ValueError(f"not a figure: {value!r}") from error
