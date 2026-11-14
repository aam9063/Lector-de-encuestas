"""The semaphore of section 7.4 and the group B flags of section 7.3.

The semaphore describes the information the news story gives, never the quality of the
poll or of the pollster, and it never names a party.

Section 7.4 only assigns a colour to specific rule ids. ``M6``, ``M7``, ``M9``, ``M12``
and ``M13`` appear in the document without a defined meaning (``M6``, ``M7`` and ``M9``
are listed as amber triggers, ``M12`` and ``M13`` have no colour at all), so they are
carried as fired ids and left inert rather than invented here.
"""

from collections.abc import Iterable
from typing import Literal

from ficha_tecnica.policy.config import PolicyConfig
from ficha_tecnica.policy.states import ItemDecision

Semaphore = Literal["red", "amber", "green", "grey"]

#: Section 7.4: these findings make the sheet red by themselves.
RED_RULES = frozenset({"M5", "M11"})
#: Section 7.4: these findings make the sheet amber by themselves.
AMBER_RULES = frozenset({"M4", "M6", "M7", "M9"})


def assign_semaphore(
    decisions: Iterable[ItemDecision],
    *,
    fired: frozenset[str],
    policy: PolicyConfig,
    veda_active: bool = False,
    poll_type: str | None = None,
) -> Semaphore:
    """Colour the sheet: grey for "not applicable", then red, amber, green."""
    if veda_active or poll_type == "not_a_poll":
        return "grey"

    if fired & RED_RULES:
        return "red"

    items = list(decisions)
    if any(
        decision.state == "absent" and decision.layer == "formal" and decision.weight == "high"
        for decision in items
    ):
        return "red"

    if fired & AMBER_RULES:
        return "amber"
    if any(
        decision.state == "absent" and decision.layer == "formal" and decision.weight == "medium"
        for decision in items
    ):
        return "amber"
    if any(decision.state == "review" for decision in items):
        return "amber"

    return "green"


def group_b_flags(
    *,
    headline_overreach_score: float | None,
    prediction_probability: float | None,
    subgroup_probability: float | None,
    self_selected_probability: float | None,
    policy: PolicyConfig,
) -> set[str]:
    """Which group B behaviours cross their configured threshold.

    Ids follow the mutation table of section 11.1 where one exists, so a flag can be
    traced back to the case that exercises it in the evaluation.
    """
    flags: set[str] = set()
    if (
        headline_overreach_score is not None
        and headline_overreach_score >= policy.headline_overreach_flag_min_score
    ):
        flags.add("M11")
    if (
        prediction_probability is not None
        and prediction_probability >= policy.prediction_flag_min_p
    ):
        flags.add("M12")
    if subgroup_probability is not None and subgroup_probability >= policy.subgroup_flag_min_p:
        flags.add("M7")
    if (
        self_selected_probability is not None
        and self_selected_probability >= policy.self_selected_flag_min_p
    ):
        flags.add("M13")
    return flags
