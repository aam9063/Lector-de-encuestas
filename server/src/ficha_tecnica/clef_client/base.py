"""The one interface the rest of the app uses to ask Clef for probabilities."""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from ficha_tecnica.clef_client.models import ClefResponse, Question


@runtime_checkable
class DecisionProvider(Protocol):
    """A single semantic decision pass over a bounded state.

    Implementations must be interchangeable: the policy only reads probabilities,
    never provider-specific fields.
    """

    async def ask(self, state: str, questions: Mapping[str, Question]) -> ClefResponse:
        """Ask every question over ``state`` and return the parsed answers."""
        ...
