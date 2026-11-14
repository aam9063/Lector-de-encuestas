"""Evaluation (ENC-16, ENC-17): synthetic corpus by construction and baseline harness.

Public surface for the ``eval/run.py`` CLI: build the corpus, run baselines, score
them and render the table and the chart. Generation is deterministic from templates
with a fixed seed; no article is ever produced by a model.
"""

from ficha_tecnica.evaluation.baselines import (
    ALL_BASELINES,
    BaselineRun,
    code_rules_fired,
    run_baseline,
    unavailable_baseline,
)
from ficha_tecnica.evaluation.dataset import (
    EVALUATION_SEED,
    EvalCase,
    Gold,
    build_dataset,
    split_of_base,
)
from ficha_tecnica.evaluation.metrics import (
    CaseJudgment,
    MetricValue,
    calibration_error,
    f1_by_item,
    false_accusation_rate,
    omission_recall,
    percentile,
    review_fraction,
    rule_accuracy,
    stability,
)
from ficha_tecnica.evaluation.render import render_chart_svg, render_table
from ficha_tecnica.evaluation.runner import BaselineRow, HarnessReport, run_harness

__all__ = [
    "ALL_BASELINES",
    "EVALUATION_SEED",
    "BaselineRow",
    "BaselineRun",
    "CaseJudgment",
    "EvalCase",
    "Gold",
    "HarnessReport",
    "MetricValue",
    "build_dataset",
    "calibration_error",
    "code_rules_fired",
    "f1_by_item",
    "false_accusation_rate",
    "omission_recall",
    "percentile",
    "render_chart_svg",
    "render_table",
    "review_fraction",
    "rule_accuracy",
    "run_baseline",
    "run_harness",
    "split_of_base",
    "stability",
    "unavailable_baseline",
]
