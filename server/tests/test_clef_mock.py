"""MockProvider: deterministic, no network, same interface as the real provider."""

import pytest

from ficha_tecnica.clef_client import (
    ChoiceAnswer,
    ChoiceQuestion,
    MockProvider,
    NoulQuestion,
    ScoreQuestion,
)

QUESTIONS = {
    "a_sample_size": NoulQuestion(instructions="How many people were interviewed?"),
    "b_poll_type": ChoiceQuestion(
        instructions="What kind of survey?",
        criteria={"voting_intention_estimate": "seats model", "not_a_poll": "not a poll"},
    ),
    "b_headline_overreach": ScoreQuestion(
        instructions="How much does the headline overreach?",
        criteria=["Nada", "Poco", "Mucho"],
    ),
}


async def test_is_deterministic() -> None:
    provider = MockProvider()

    first = await provider.ask("cualquier texto", QUESTIONS)
    second = await provider.ask("cualquier texto", QUESTIONS)

    assert first.answers == second.answers


async def test_covers_every_question_and_sums_to_one() -> None:
    provider = MockProvider()

    response = await provider.ask("cualquier texto", QUESTIONS)

    assert set(response.answers) == set(QUESTIONS)
    for answer in response.answers.values():
        assert sum(answer.probabilities.values()) == pytest.approx(1.0)


async def test_overrides_let_a_test_pin_a_probability() -> None:
    provider = MockProvider(noul_probabilities={"a_sample_size": 0.97})

    response = await provider.ask("cualquier texto", QUESTIONS)

    assert response.answers["a_sample_size"].yes_probability() == pytest.approx(0.97)


async def test_rejects_an_override_for_an_unknown_question() -> None:
    provider = MockProvider(noul_probabilities={"no_existe": 0.5})

    with pytest.raises(ValueError, match="no_existe"):
        await provider.ask("cualquier texto", QUESTIONS)


async def test_choice_picks_the_option_with_the_most_probability() -> None:
    provider = MockProvider(choice_probabilities={"b_poll_type": "not_a_poll"})

    response = await provider.ask("cualquier texto", QUESTIONS)

    answer = response.answers["b_poll_type"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice == "not_a_poll"
    assert answer.probabilities["not_a_poll"] > answer.probabilities["voting_intention_estimate"]
