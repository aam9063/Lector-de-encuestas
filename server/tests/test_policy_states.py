"""Table 7.2, cell by cell.

Every cell of the design document's state table gets a test, plus the M14 evaluation
mutation (a paraphrase that must NOT be accused of omitting anything). The asymmetry
under test: with a code candidate, an item can never be reported absent.
"""

import pytest

from ficha_tecnica.policy.config import PolicyConfig
from ficha_tecnica.policy.states import ItemState, decide_item, finalize_item

POLICY = PolicyConfig()


def decide(
    *,
    has_candidate: bool,
    probability: float,
    layer: str = "formal",
    item_id: str = "a_sample_size",
    external: float | None = None,
) -> ItemState:
    return decide_item(
        item_id=item_id,
        layer=layer,  # type: ignore[arg-type]
        has_candidate=has_candidate,
        probability=probability,
        external_sheet_probability=external,
        policy=POLICY,
    )


@pytest.mark.parametrize(
    ("probability", "expected"),
    [(0.50, "present"), (0.80, "present"), (1.0, "present"), (0.51, "present")],
)
def test_candidate_present_with_clef_agreement(probability: float, expected: ItemState) -> None:
    assert decide(has_candidate=True, probability=probability) == expected


@pytest.mark.parametrize("probability", [0.0, 0.10, 0.20, 0.49])
def test_candidate_never_becomes_absent(probability: float) -> None:
    """The safety property: code found evidence, so the app must not accuse omission."""
    state = decide(has_candidate=True, probability=probability)

    assert state != "absent"
    assert state == "needs_second_reading"


@pytest.mark.parametrize(("probability", "expected"), [(0.80, "present"), (0.95, "present")])
def test_no_candidate_but_clef_is_sure_it_is_present(
    probability: float, expected: ItemState
) -> None:
    assert decide(has_candidate=False, probability=probability) == expected


@pytest.mark.parametrize("probability", [0.0, 0.05, 0.10])
def test_no_candidate_and_clef_is_sure_it_is_absent(probability: float) -> None:
    assert decide(has_candidate=False, probability=probability) == "absent"


@pytest.mark.parametrize("probability", [0.11, 0.35, 0.79])
def test_no_candidate_and_clef_is_unsure(probability: float) -> None:
    assert decide(has_candidate=False, probability=probability) == "needs_second_reading"


def test_external_sheet_turns_a_missing_item_into_a_reference() -> None:
    assert (
        decide(
            has_candidate=False,
            probability=0.30,
            item_id="a_sample_size",
            external=0.90,
        )
        == "refers_external"
    )


def test_external_sheet_does_not_override_a_proven_present_item() -> None:
    assert (
        decide(has_candidate=False, probability=0.85, item_id="a_sample_size", external=0.95)
        == "present"
    )


def test_external_sheet_below_threshold_is_ignored() -> None:
    assert (
        decide(has_candidate=False, probability=0.30, item_id="a_sample_size", external=0.50)
        == "needs_second_reading"
    )


def test_the_external_sheet_item_itself_is_never_marked_as_referring() -> None:
    """The item that asks "do you point elsewhere?" cannot itself be answered "elsewhere"."""
    assert (
        decide(
            has_candidate=False,
            probability=0.95,
            item_id="a_external_sheet",
            external=0.95,
        )
        == "present"
    )


def test_non_formal_layers_go_straight_to_review_instead_of_a_second_reading() -> None:
    state = decide(has_candidate=False, probability=0.45, layer="methodological")

    assert state == "review"


def test_m14_paraphrase_is_never_a_false_accusation() -> None:
    """M14 rewrites wording without changing content: labels must not move.

    The code finds no candidate because the wording changed ("error muestral" instead of
    "margen de error"), but Clef recognises the item, so the state stays present instead
    of collapsing to absent.
    """
    assert decide(has_candidate=False, probability=0.93) == "present"


@pytest.mark.parametrize(
    ("second_reading", "expected"),
    [(0.95, "present"), (0.80, "present"), (0.10, "absent"), (0.05, "absent")],
)
def test_second_reading_confirms_and_closes_the_item(
    second_reading: float, expected: ItemState
) -> None:
    assert finalize_item(has_candidate=False, probability=second_reading, policy=POLICY) == expected


@pytest.mark.parametrize("second_reading", [0.11, 0.45, 0.60, 0.79])
def test_a_persistent_doubt_ends_in_review(second_reading: float) -> None:
    assert finalize_item(has_candidate=False, probability=second_reading, policy=POLICY) == "review"


def test_second_reading_never_accuses_when_the_code_found_a_candidate() -> None:
    """After two readings the doubt is over: the honest outcome is review, not absent."""
    assert finalize_item(has_candidate=True, probability=0.05, policy=POLICY) == "review"


def test_thresholds_come_from_configuration_not_from_the_code() -> None:
    strict = PolicyConfig.model_validate(
        {
            "version": 1,
            "thresholds": {
                "present_with_candidate": 0.90,
                "present_without_candidate": 0.95,
                "absent_max": 0.05,
                "gray_band": [0.20, 0.80],
            },
            "second_reading_for_layers": ["formal"],
        }
    )

    assert (
        decide_item(
            item_id="a_sample_size",
            layer="formal",
            has_candidate=True,
            probability=0.60,
            policy=strict,
        )
        == "needs_second_reading"
    )
