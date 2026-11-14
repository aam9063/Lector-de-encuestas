"""Provider errors. Each one maps to a distinct failure the API must report honestly."""


class ClefError(RuntimeError):
    """Base class for every failure talking to Clef."""


class ClefAuthError(ClefError):
    """401/403: the key is invalid or lacks permission. Never retried."""


class ClefBadRequestError(ClefError):
    """400/413: the request itself is wrong (bad criteria, oversized state)."""


class ClefTimeoutError(ClefError):
    """The request exceeded the configured timeout."""


class ClefUnavailableError(ClefError):
    """429 sustained past the attempt budget: NaN's two-in-flight limit is saturated."""
