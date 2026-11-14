"""ENC-10: the blackout switch (section 7.6).

The legal window is the five days before the vote. Being off by one hour here means
publishing a poll result when publishing is forbidden, so the boundaries are tested
explicitly, on both sides, in the window's own timezone.

Analysing a news story is not publishing it, but the design is deliberately conservative:
inside the window, an electoral poll gets a notice and no findings.
"""

from datetime import UTC, datetime, timedelta

import pytest

from ficha_tecnica.policy.config import load_policy
from ficha_tecnica.policy.veda import (
    VEDA_NOTICE,
    VedaConfig,
    resolve_now,
    should_block,
    veda_notice,
    within_window,
)

POLICY = load_policy()
VEDA = POLICY.veda

# 2026-11-24T00:00+01:00 is the first forbidden instant; the vote is on the 29th and the
# window reopens at 2026-11-30T00:00+01:00.
BEFORE = datetime(2026, 11, 23, 23, 59, 59, tzinfo=VEDA.start.tzinfo)
AT_START = VEDA.start
MIDDLE = datetime(2026, 11, 27, 12, 0, tzinfo=VEDA.start.tzinfo)
LAST_SECOND = VEDA.end - timedelta(seconds=1)
AT_END = VEDA.end


def test_the_configured_window_matches_the_documented_dates() -> None:
    assert VEDA.start.isoformat() == "2026-11-24T00:00:00+01:00"
    assert VEDA.end.isoformat() == "2026-11-30T00:00:00+01:00"
    assert VEDA.mode == "strict"


@pytest.mark.parametrize(
    ("when", "expected"),
    [(BEFORE, False), (AT_START, True), (MIDDLE, True)],
)
def test_window_boundaries(when: datetime, expected: bool) -> None:
    assert within_window(when, VEDA) is expected


def test_the_window_is_half_open_so_the_end_instant_is_outside() -> None:
    assert within_window(LAST_SECOND, VEDA) is True
    assert within_window(AT_END, VEDA) is False


def test_the_same_instant_in_utc_is_the_same_answer() -> None:
    """The window is absolute, not a wall clock: 23:00Z equals 00:00+01:00."""
    assert within_window(AT_START.astimezone(UTC), VEDA) is True


def test_a_naive_datetime_is_rejected() -> None:
    """Silently assuming a timezone is how a blackout opens an hour early."""
    with pytest.raises(ValueError, match="timezone"):
        within_window(datetime(2026, 11, 25, 12, 0), VEDA)


def test_mode_off_never_blocks() -> None:
    off = VedaConfig.model_validate(
        {
            "mode": "off",
            "start": VEDA.start,
            "end": VEDA.end,
            "block_if_p_electoral_at_least": 0.35,
        }
    )

    assert should_block(when=MIDDLE, is_electoral=0.99, poll_type="not_a_poll", veda=off) is False
    assert within_window(MIDDLE, off) is False


class TestShouldBlock:
    """Inside the window, only electoral polls are refused."""

    def test_an_electoral_poll_at_the_threshold_is_blocked(self) -> None:
        assert (
            should_block(
                when=MIDDLE,
                is_electoral=0.35,
                poll_type="issue_opinion",
                veda=VEDA,
            )
            is True
        )

    def test_just_below_the_threshold_is_not_blocked(self) -> None:
        assert (
            should_block(
                when=MIDDLE,
                is_electoral=0.34,
                poll_type="issue_opinion",
                veda=VEDA,
            )
            is False
        )

    @pytest.mark.parametrize("poll_type", ["voting_intention_estimate", "direct_voting_intention"])
    def test_a_voting_intention_poll_is_blocked_even_with_a_low_probability(
        self, poll_type: str
    ) -> None:
        assert should_block(when=MIDDLE, is_electoral=0.10, poll_type=poll_type, veda=VEDA) is True

    def test_a_poll_about_other_topics_is_analysed_inside_the_window(self) -> None:
        assert (
            should_block(
                when=MIDDLE,
                is_electoral=0.05,
                poll_type="issue_opinion",
                veda=VEDA,
            )
            is False
        )

    def test_nothing_is_blocked_outside_the_window(self) -> None:
        assert (
            should_block(
                when=BEFORE,
                is_electoral=0.99,
                poll_type="direct_voting_intention",
                veda=VEDA,
            )
            is False
        )


def test_the_notice_states_the_dates_and_never_a_finding() -> None:
    notice = veda_notice(VEDA)

    assert VEDA_NOTICE in notice
    assert "24" in notice and "29" in notice
    assert "%" not in notice


def test_veda_now_lets_the_demo_simulate_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VEDA_NOW", "2026-11-25T10:00:00+01:00")

    assert resolve_now(VEDA) == datetime(2026, 11, 25, 10, 0, tzinfo=VEDA.start.tzinfo)


def test_without_the_override_the_clock_is_the_system_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VEDA_NOW", raising=False)

    resolved = resolve_now(VEDA)

    assert resolved.tzinfo is not None
    assert resolved.year >= 2026


def test_a_malformed_veda_now_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VEDA_NOW", "manana a las cinco")

    with pytest.raises(ValueError, match="VEDA_NOW"):
        resolve_now(VEDA)


def test_a_veda_now_without_timezone_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VEDA_NOW", "2026-11-25T10:00:00")

    with pytest.raises(ValueError, match="timezone"):
        resolve_now(VEDA)
