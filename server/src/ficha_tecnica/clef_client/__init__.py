"""DecisionProvider interface to Clef: `nan` and `mock` adapters, 2-request semaphore."""

from ficha_tecnica.clef_client.base import DecisionProvider
from ficha_tecnica.clef_client.errors import (
    ClefAuthError,
    ClefBadRequestError,
    ClefError,
    ClefTimeoutError,
    ClefUnavailableError,
)
from ficha_tecnica.clef_client.mock import MockProvider
from ficha_tecnica.clef_client.models import (
    ChoiceAnswer,
    ChoiceQuestion,
    ClefResponse,
    NoulAnswer,
    NoulQuestion,
    Question,
    ScoreAnswer,
    ScoreQuestion,
)
from ficha_tecnica.clef_client.nan import NanProvider

__all__ = [
    "ChoiceAnswer",
    "ChoiceQuestion",
    "ClefAuthError",
    "ClefBadRequestError",
    "ClefError",
    "ClefResponse",
    "ClefTimeoutError",
    "ClefUnavailableError",
    "DecisionProvider",
    "MockProvider",
    "NanProvider",
    "NoulAnswer",
    "NoulQuestion",
    "Question",
    "ScoreAnswer",
    "ScoreQuestion",
]
