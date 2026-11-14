"""Item states: the asymmetric table 7.2 of the design document.

The asymmetry is the product's safety property, not a tuning detail:

- when the code found a candidate, the item can never be reported ``absent``: the app
  does not accuse a news story of omitting something it actually mentioned;
- ``absent`` requires no candidate *and* a low probability;
- a doubt never resolves into an accusation; it becomes a second reading and, if the
  doubt persists, ``review`` -- "we are not sure, look here".

``needs_second_reading`` is an internal state, not a status shown to the user: it tells
the orchestrator (ENC-12) to ask Clef again with a focused state.
"""

from dataclasses import dataclass
from typing import Literal

from ficha_tecnica.policy.config import PolicyConfig

Layer = Literal["formal", "methodological", "auxiliary"]
Weight = Literal["high", "medium", "low"]
ItemState = Literal["present", "absent", "refers_external", "review", "needs_second_reading"]

#: The item asking "do you point to a sheet published elsewhere?" cannot itself be
#: answered "elsewhere", or the escape hatch would close on itself.
EXTERNAL_SHEET_ITEM = "a_external_sheet"
EXTERNAL_SHEET_MIN = 0.80
EXTERNAL_SHEET_MAX_ITEM_P = 0.50


@dataclass(frozen=True)
class ItemDecision:
    """One item's outcome, ready for the semaphore and the report."""

    item_id: str
    layer: Layer
    weight: Weight
    state: ItemState


def _doubt(layer: Layer, policy: PolicyConfig) -> ItemState:
    """What to do with an unresolved item: ask again, or hand it to the reader."""
    return "needs_second_reading" if layer in policy.second_reading_for_layers else "review"


def decide_item(
    *,
    item_id: str,
    layer: Layer,
    has_candidate: bool,
    probability: float,
    policy: PolicyConfig,
    external_sheet_probability: float | None = None,
) -> ItemState:
    """Assign the state of one item from the code candidate and Clef's probability.

    Order matters. A confident absence is decided before the external-sheet escape hatch:
    the evaluation showed that every news story linking the technical sheet turned all 28
    items with a missing datum into ``refers_external``, which made the state that says
    "this is missing" unreachable and drove recall of omissions to 6.67 %. The story did
    omit the datum; linking a sheet does not put it back. The reference only softens a
    doubt, where we genuinely cannot tell.
    """
    if has_candidate:
        if probability >= policy.thresholds.present_with_candidate:
            return "present"
        # Never "absent": the code found evidence, so the doubt stays open.
        return _doubt(layer, policy)

    if probability >= policy.thresholds.present_without_candidate:
        return "present"
    if probability <= policy.thresholds.absent_max:
        return "absent"

    if (
        external_sheet_probability is not None
        and item_id != EXTERNAL_SHEET_ITEM
        and external_sheet_probability >= EXTERNAL_SHEET_MIN
    ):
        return "refers_external"

    return _doubt(layer, policy)


def finalize_item(
    *,
    has_candidate: bool,
    probability: float,
    policy: PolicyConfig,
) -> ItemState:
    """Close a grey item after the focused second reading.

    There is nothing to read again at this point, so a doubt that survives becomes
    ``review``: the app says it is not sure and shows the reader where to look.
    """
    if has_candidate and probability >= policy.thresholds.present_with_candidate:
        return "present"
    if has_candidate:
        return "review"
    if probability >= policy.thresholds.present_without_candidate:
        return "present"
    if probability <= policy.thresholds.absent_max:
        return "absent"
    return "review"
