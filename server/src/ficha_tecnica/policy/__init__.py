"""Policy: asymmetric thresholds, item states, margin calculator, blackout (veda) switch."""

from ficha_tecnica.policy.calculator import (
    THEORETICAL_MARGINS,
    fired_rules,
    lead_ratio,
    lead_verdict,
    margin_is_implausible,
    theoretical_margin,
)
from ficha_tecnica.policy.config import PolicyConfig, Thresholds, load_policy
from ficha_tecnica.policy.semaphore import Semaphore, assign_semaphore, group_b_flags
from ficha_tecnica.policy.states import (
    ItemDecision,
    ItemState,
    Layer,
    Weight,
    decide_item,
    finalize_item,
)
from ficha_tecnica.policy.veda import (
    VEDA_NOTICE,
    VedaConfig,
    resolve_now,
    should_block,
    veda_notice,
    within_window,
)

__all__ = [
    "THEORETICAL_MARGINS",
    "VEDA_NOTICE",
    "ItemDecision",
    "ItemState",
    "Layer",
    "PolicyConfig",
    "Semaphore",
    "Thresholds",
    "VedaConfig",
    "Weight",
    "assign_semaphore",
    "decide_item",
    "finalize_item",
    "fired_rules",
    "group_b_flags",
    "lead_ratio",
    "lead_verdict",
    "load_policy",
    "margin_is_implausible",
    "resolve_now",
    "should_block",
    "theoretical_margin",
    "veda_notice",
    "within_window",
]
