"""The blackout switch (section 7.6).

Spain forbids publishing, spreading or reproducing electoral polls during the five days
before the vote (LOREG art. 69.7). Analysing a story is not publishing one, but the design
is conservative: inside the window an electoral poll gets a notice and no findings, while
polls about other topics keep being analysed.

The window is read from configuration, never from the browser clock, and every instant must
carry a timezone: silently assuming one is how a blackout opens an hour early.

The exact window is still `[VERIFICAR]` with the JEC (verification item 4 of the design).
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict

#: Poll types that are electoral by nature, blocked regardless of the probability.
VOTING_INTENTION_TYPES = frozenset({"voting_intention_estimate", "direct_voting_intention"})

VEDA_NOTICE = "Aviso de veda electoral: esta noticia trata de encuestas electorales."

_DEFAULT_TZ = timezone(timedelta(hours=1))


class VedaConfig(BaseModel):
    """The blackout window and the probability that turns a story into an electoral poll."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["strict", "off"] = "strict"
    start: datetime = datetime(2026, 11, 24, tzinfo=_DEFAULT_TZ)
    end: datetime = datetime(2026, 11, 30, tzinfo=_DEFAULT_TZ)
    block_if_p_electoral_at_least: float = 0.35


def _require_aware(when: datetime) -> None:
    if when.tzinfo is None:
        raise ValueError("a timezone is required: a naive datetime could open the window early")


def within_window(when: datetime, veda: VedaConfig) -> bool:
    """True inside the forbidden window. The window is half-open: ``end`` is outside."""
    _require_aware(when)
    if veda.mode == "off":
        return False
    return veda.start <= when < veda.end


def should_block(
    *,
    when: datetime,
    is_electoral: float | None,
    poll_type: str | None,
    veda: VedaConfig,
) -> bool:
    """Inside the window, refuse an electoral poll and nothing else."""
    if not within_window(when, veda):
        return False
    if poll_type in VOTING_INTENTION_TYPES:
        return True
    return is_electoral is not None and is_electoral >= veda.block_if_p_electoral_at_least


def veda_notice(veda: VedaConfig) -> str:
    """The notice shown instead of findings. It carries no figures and no party names.

    It does not repeat the legal disclaimer: the pipeline appends that separately, and the
    first version said the same thing twice, which reads as a template that nobody checked.
    """
    voting_day = (veda.end - timedelta(days=1)).date()
    return (
        f"{VEDA_NOTICE} La ley prohíbe publicar sondeos electorales en los cinco días "
        f"previos a la votación, del {veda.start:%d/%m/%Y} al {voting_day:%d/%m/%Y} "
        f"(votación el {voting_day:%d/%m/%Y}). No se emiten hallazgos."
    )


def resolve_now(veda: VedaConfig) -> datetime:
    """The instant to judge, with ``VEDA_NOW`` allowed so a demo can simulate the window."""
    override = os.environ.get("VEDA_NOW")
    if not override:
        return datetime.now(tz=veda.start.tzinfo)
    try:
        parsed = datetime.fromisoformat(override)
    except ValueError as error:
        raise ValueError(
            f"VEDA_NOW is not an ISO 8601 instant: {override!r}. Example: 2026-11-25T10:00:00+01:00"
        ) from error
    _require_aware(parsed)
    return parsed
