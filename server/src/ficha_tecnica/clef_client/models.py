"""Wire models for the Clef API (contract captured in docs/clef-contract.md).

Two directions:

- Questions we send: ``NoulQuestion``, ``ChoiceQuestion``, ``ScoreQuestion``.
  ``choice`` takes ``criteria`` as an object of label -> description and ``score``
  takes ``criteria`` as an ordered list of levels. Both were verified against the
  live API: any other field name is rejected with 400.
- Answers we receive: a discriminated union on ``type`` so the policy can read a
  probability without caring which shape produced it.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# --- questions we send -------------------------------------------------------------


class _Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str


class NoulQuestion(_Question):
    type: Literal["noul"] = "noul"


class ChoiceQuestion(_Question):
    type: Literal["choice"] = "choice"
    criteria: dict[str, str] = Field(min_length=2)


class ScoreQuestion(_Question):
    type: Literal["score"] = "score"
    criteria: list[str] = Field(min_length=2)


Question = NoulQuestion | ChoiceQuestion | ScoreQuestion


# --- answers we receive ------------------------------------------------------------


class _Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    confidence: float

    def yes_probability(self) -> float:
        """Probability that the question is answered "yes" (the policy's only need)."""
        raise NotImplementedError


class NoulAnswer(_Answer):
    type: Literal["noul"]
    noul: float
    probabilities: dict[str, float]

    def yes_probability(self) -> float:
        return self.probabilities.get("yes", self.noul)


class ChoiceAnswer(_Answer):
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, float]

    def yes_probability(self) -> float:
        """A ``choice`` question has no yes/no reading; its confidence is exposed."""
        return self.confidence


class ScoreAnswer(_Answer):
    type: Literal["score"]
    score: float
    legend: dict[str, str]
    probabilities: dict[str, float]

    def yes_probability(self) -> float:
        """A ``score`` answer is ordered: the top level's probability is the signal."""
        return self.probabilities[max(self.probabilities, key=int)]


Answer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class Usage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    input_tokens: int
    output_tokens: int


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label_mass: float | None = None
    argmax_is_label: bool | None = None


class ClefResponse(BaseModel):
    """The response envelope. Unknown fields are ignored so a new API field cannot break us."""

    model_config = ConfigDict(extra="ignore")

    id: str
    object: str
    created: int
    model: str
    answers: dict[str, Answer]
    usage: Usage
    diagnostics: dict[str, Diagnostic] = {}
    joint: dict | None = None
