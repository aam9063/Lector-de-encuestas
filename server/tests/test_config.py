"""Config YAMLs must parse and expose the v1 shape expected by the pipeline."""

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> dict[str, Any]:
    with (REPO_ROOT / "config" / name).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_checklist_v1() -> None:
    checklist = _load("checklist.v1.yaml")
    assert checklist["version"] == 1
    ids = [item["id"] for item in checklist["items"]]
    assert len(ids) == len(set(ids))
    for required in ["a_sample_size", "a_margin", "a_fieldwork_dates", "a_entity"]:
        assert required in ids
    for item in checklist["items"]:
        assert item["layer"] in {"formal", "methodological", "auxiliary"}
        assert item["weight"] in {"high", "medium", "low"}


def test_questionnaire_v1_groups() -> None:
    questionnaire = _load("questionnaire.v1.yaml")
    assert questionnaire["version"] == 1
    assert set(questionnaire["groups"]) == {"A", "B", "C"}
    group_a_ids = {question["id"] for question in questionnaire["groups"]["A"]}
    assert len(group_a_ids) == 15
    group_b = {question["id"] for question in questionnaire["groups"]["B"]}
    assert {"b_poll_type", "b_is_electoral", "b_headline_overreach"} <= group_b


def test_policy_v1_and_veda() -> None:
    policy = _load("policy.yaml")
    thresholds = policy["policy"]["thresholds"]
    assert thresholds["present_with_candidate"] == 0.50
    assert thresholds["present_without_candidate"] == 0.80
    assert thresholds["gray_band"] == [0.20, 0.80]
    veda = policy["veda"]
    assert veda["mode"] in {"strict", "off"}
    assert veda["block_if_p_electoral_at_least"] == 0.35


def test_pollsters_and_parties() -> None:
    pollsters = _load("pollsters.yaml")
    parties = _load("parties.yaml")
    assert pollsters["version"] == parties["version"] == 1
    assert len(pollsters["pollsters"]) > 0
    names = [party["name"] for party in parties["parties"]]
    assert len(names) == len(set(names))
    for party in parties["parties"]:
        assert party["variants"], f"party {party['name']} needs at least one variant"
