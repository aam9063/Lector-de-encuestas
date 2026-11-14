"""Policy thresholds are loaded from config/policy.yaml, not hard-coded."""

import pytest

from ficha_tecnica.policy.config import PolicyConfig, load_policy


def test_defaults_match_the_yaml_file() -> None:
    """A drift between the YAML and the defaults is a silent behaviour change."""
    from_file = load_policy()

    assert from_file == PolicyConfig()


def test_threshold_values_come_from_the_documented_table() -> None:
    policy = load_policy()

    assert policy.thresholds.present_with_candidate == 0.50
    assert policy.thresholds.present_without_candidate == 0.80
    assert policy.thresholds.absent_max == 0.10
    assert policy.thresholds.gray_band == (0.20, 0.80)
    assert policy.second_reading_for_layers == ("formal",)


def test_flag_thresholds_match_the_documented_ones() -> None:
    policy = load_policy()

    assert policy.headline_overreach_flag_min_score == 3
    assert policy.prediction_flag_min_p == 0.70
    assert policy.subgroup_flag_min_p == 0.70
    assert policy.self_selected_flag_min_p == 0.60


def test_an_absent_threshold_above_the_present_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="absent_max"):
        PolicyConfig.model_validate(
            {
                "version": 1,
                "thresholds": {
                    "present_with_candidate": 0.50,
                    "present_without_candidate": 0.30,
                    "absent_max": 0.40,
                    "gray_band": [0.20, 0.80],
                },
                "second_reading_for_layers": ["formal"],
            }
        )
