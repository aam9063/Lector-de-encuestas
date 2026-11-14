"""Deterministic provider for tests, offline demos and CI.

It answers every question from a fixed rule so a wiring change cannot silently alter a
policy test: a ``noul`` question defaults to 0.5 (the middle of the grey band, which
forces the policy to reason), a ``choice`` question spreads probability evenly, and a
``score`` question too. Tests pin a specific value through the ``*_probabilities``
overrides instead of relying on those defaults.
"""

from collections.abc import Mapping

from ficha_tecnica.clef_client.errors import ClefBadRequestError
from ficha_tecnica.clef_client.models import (
    ChoiceAnswer,
    ChoiceQuestion,
    ClefResponse,
    Diagnostic,
    NoulAnswer,
    NoulQuestion,
    Question,
    ScoreAnswer,
    ScoreQuestion,
    Usage,
)

DEFAULT_NOUL = 0.5
PINNED_CHOICE_PROBABILITY = 0.9


class MockProvider:
    """``DecisionProvider`` that never touches the network."""

    def __init__(
        self,
        *,
        noul_probabilities: Mapping[str, float] | None = None,
        choice_probabilities: Mapping[str, str] | None = None,
        score_positions: Mapping[str, float] | None = None,
    ) -> None:
        self._noul = dict(noul_probabilities or {})
        self._choice = dict(choice_probabilities or {})
        self._score = dict(score_positions or {})

    async def ask(self, state: str, questions: Mapping[str, Question]) -> ClefResponse:
        self._reject_unknown_overrides(questions)

        answers = {}
        for question_id, question in questions.items():
            if isinstance(question, NoulQuestion):
                answers[question_id] = self._noul_answer(question_id)
            elif isinstance(question, ChoiceQuestion):
                answers[question_id] = self._choice_answer(question_id, question)
            elif isinstance(question, ScoreQuestion):
                answers[question_id] = self._score_answer(question_id, question)
            else:  # pragma: no cover - the union is closed
                raise TypeError(f"unsupported question type for {question_id}")

        return ClefResponse(
            id="decision-mock",
            object="structured_decision",
            created=0,
            model="clef",
            answers=answers,
            usage=Usage(input_tokens=len(state) // 4, output_tokens=0),
            diagnostics={
                question_id: Diagnostic(label_mass=1.0, argmax_is_label=True)
                for question_id in questions
            },
            joint=None,
        )

    def _reject_unknown_overrides(self, questions: Mapping[str, Question]) -> None:
        for question_id in (*self._noul, *self._choice, *self._score):
            if question_id not in questions:
                raise ValueError(
                    f"mock override for unknown question {question_id!r}; "
                    f"known ids: {sorted(questions)}"
                )

    def _noul_answer(self, question_id: str) -> NoulAnswer:
        probability = self._noul.get(question_id, DEFAULT_NOUL)
        if not 0.0 <= probability <= 1.0:
            raise ClefBadRequestError(f"noul override for {question_id} is not a probability")
        return NoulAnswer(
            type="noul",
            noul=probability,
            probabilities={"yes": probability, "no": 1.0 - probability},
            confidence=probability,
        )

    def _choice_answer(self, question_id: str, question: ChoiceQuestion) -> ChoiceAnswer:
        labels = list(question.criteria)
        pinned = self._choice.get(question_id)
        if pinned is None:
            share = 1.0 / len(labels)
            probabilities = dict.fromkeys(labels, share)
            chosen = labels[0]
        else:
            if pinned not in labels:
                raise ValueError(
                    f"mock pin {pinned!r} is not a criterion of {question_id!r}: {labels}"
                )
            rest = (1.0 - PINNED_CHOICE_PROBABILITY) / (len(labels) - 1)
            probabilities = {
                label: PINNED_CHOICE_PROBABILITY if label == pinned else rest for label in labels
            }
            chosen = pinned
        return ChoiceAnswer(
            type="choice",
            choice=chosen,
            probabilities=probabilities,
            confidence=probabilities[chosen],
        )

    def _score_answer(self, question_id: str, question: ScoreQuestion) -> ScoreAnswer:
        levels = question.criteria
        share = 1.0 / len(levels)
        probabilities = {str(index): share for index in range(len(levels))}
        position = self._score.get(question_id, (len(levels) - 1) / 2)
        if not 0.0 <= position <= len(levels) - 1:
            raise ValueError(
                f"score override for {question_id} must be between 0 and {len(levels) - 1}"
            )
        return ScoreAnswer(
            type="score",
            score=position,
            legend={str(index): level for index, level in enumerate(levels)},
            probabilities=probabilities,
            confidence=max(probabilities.values()),
        )
