"""Policy thresholds loaded from ``config/policy.yaml`` (section 7.2).

The defaults in this module and the YAML file must stay identical: a silent drift between
them would change when the app accuses a news story of omitting information, which is the
costliest mistake this tool can make.
"""

from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


class Thresholds(BaseModel):
    """Asymmetric thresholds: accusing requires far more certainty than confirming."""

    model_config = ConfigDict(extra="forbid")

    present_with_candidate: float = 0.50
    present_without_candidate: float = 0.80
    absent_max: float = 0.10
    gray_band: tuple[float, float] = (0.20, 0.80)


class PolicyConfig(BaseModel):
    """The whole policy v1: thresholds, which layers get a second reading, B flags."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    thresholds: Thresholds = Thresholds()
    second_reading_for_layers: tuple[str, ...] = ("formal",)
    headline_overreach_flag_min_score: int = 3
    prediction_flag_min_p: float = 0.70
    subgroup_flag_min_p: float = 0.70
    self_selected_flag_min_p: float = 0.60
    lead_decisive_flag_min_p: Decimal = Decimal("0.70")
    # M4: a declared margin below this share of the theoretical one is a warning.
    declared_below_theoretical_ratio: Decimal = Decimal("0.90")
    # M5: r = lead / margin, compared against these two boundaries.
    lead_ratio_within_margin: Decimal = Decimal("1.0")
    lead_ratio_aapor_min: Decimal = Decimal("2.0")

    @model_validator(mode="after")
    def _absent_must_be_below_present(self) -> PolicyConfig:
        if self.thresholds.absent_max >= self.thresholds.present_without_candidate:
            raise ValueError(
                "absent_max must be below present_without_candidate, otherwise the same "
                "probability would be both absent and present"
            )
        return self


def load_policy(path: Path | None = None) -> PolicyConfig:
    """Read the policy from disk (``config/policy.yaml`` by default).

    The file keeps the arithmetic settings in their own top-level sections (``margin``
    and ``lead_ratio``) because they read as rules, not as accusation thresholds; they
    are folded into the flat model here so the code has one source of truth.
    """
    source = path or (_CONFIG_DIR / "policy.yaml")
    with source.open(encoding="utf-8") as stream:
        data: dict[str, dict[str, object]] = yaml.safe_load(stream)

    merged: dict[str, object] = dict(data["policy"])
    margin = data.get("margin") or {}
    if "declared_below_theoretical_ratio" in margin:
        merged["declared_below_theoretical_ratio"] = margin["declared_below_theoretical_ratio"]
    lead = data.get("lead_ratio") or {}
    for source_key, target_key in (
        ("within_margin", "lead_ratio_within_margin"),
        ("aapor_min", "lead_ratio_aapor_min"),
    ):
        if source_key in lead:
            merged[target_key] = lead[source_key]

    return PolicyConfig.model_validate(merged)
