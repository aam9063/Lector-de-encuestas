"""Semaphore 7.4 and the group B flags from 7.3."""

import pytest

from ficha_tecnica.policy.config import PolicyConfig
from ficha_tecnica.policy.semaphore import assign_semaphore, group_b_flags
from ficha_tecnica.policy.states import ItemDecision

POLICY = PolicyConfig()


def decision(item_id: str, layer: str, weight: str, state: str) -> ItemDecision:
    return ItemDecision(item_id=item_id, layer=layer, weight=weight, state=state)  # type: ignore[arg-type]


def test_all_present_gives_green() -> None:
    decisions = [decision("a_sample_size", "formal", "high", "present")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "green"


def test_a_missing_high_weight_formal_item_is_red() -> None:
    decisions = [decision("a_sample_size", "formal", "high", "absent")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "red"


def test_a_missing_medium_weight_formal_item_is_amber() -> None:
    decisions = [decision("a_entity_address", "formal", "medium", "absent")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "amber"


def test_a_missing_low_weight_formal_item_does_not_colour_the_semaphore() -> None:
    """Section 7.4 only gives a colour to high and medium formal absences."""
    decisions = [decision("a_nonresponse", "formal", "low", "absent")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "green"


def test_a_missing_methodological_item_never_colours_the_semaphore() -> None:
    decisions = [decision("a_weighting", "methodological", "low", "absent")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "green"


def test_an_item_in_review_is_amber() -> None:
    decisions = [decision("a_margin", "formal", "high", "review")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "amber"


@pytest.mark.parametrize("rule", ["M5", "M11"])
def test_these_rules_force_red(rule: str) -> None:
    assert assign_semaphore([], fired=frozenset({rule}), policy=POLICY) == "red"


@pytest.mark.parametrize("rule", ["M4", "M6", "M7", "M9"])
def test_these_rules_force_amber(rule: str) -> None:
    assert assign_semaphore([], fired=frozenset({rule}), policy=POLICY) == "amber"


def test_a_rule_without_a_documented_colour_stays_inert() -> None:
    """M12 and M13 exist as findings but section 7.4 gives them no colour."""
    assert assign_semaphore([], fired=frozenset({"M12", "M13"}), policy=POLICY) == "green"


def test_an_unknown_fired_rule_changes_nothing() -> None:
    assert assign_semaphore([], fired=frozenset({"M99"}), policy=POLICY) == "green"


def test_a_reference_to_an_external_sheet_is_not_a_missing_item() -> None:
    decisions = [decision("a_sample_size", "formal", "high", "refers_external")]

    assert assign_semaphore(decisions, fired=frozenset(), policy=POLICY) == "green"


def test_veda_wins_over_everything() -> None:
    decisions = [decision("a_sample_size", "formal", "high", "absent")]

    assert (
        assign_semaphore(decisions, fired=frozenset({"M5"}), policy=POLICY, veda_active=True)
        == "grey"
    )


def test_not_a_poll_is_grey() -> None:
    decisions = [decision("a_sample_size", "formal", "high", "absent")]

    assert (
        assign_semaphore(decisions, fired=frozenset(), policy=POLICY, poll_type="not_a_poll")
        == "grey"
    )


def test_group_b_flags_are_raised_at_their_thresholds() -> None:
    flags = group_b_flags(
        headline_overreach_score=3.0,
        prediction_probability=0.75,
        subgroup_probability=0.71,
        self_selected_probability=0.62,
        policy=POLICY,
    )

    assert flags == {"M11", "M12", "M7", "M13"}


def test_group_b_flags_stay_silent_below_their_thresholds() -> None:
    flags = group_b_flags(
        headline_overreach_score=2.9,
        prediction_probability=0.69,
        subgroup_probability=0.69,
        self_selected_probability=0.59,
        policy=POLICY,
    )

    assert flags == set()
