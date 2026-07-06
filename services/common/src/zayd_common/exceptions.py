class StateTransitionError(ValueError):
    """Base exception for all state machine transition errors."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class InvalidStateTransitionError(StateTransitionError):
    """Raised when a state transition is not allowed by the state machine rules."""

    def __init__(self, error_code: str, from_state: str, to_state: str) -> None:
        message = f"Invalid state transition from '{from_state}' to '{to_state}'."
        super().__init__(error_code, message)
        self.from_state = from_state
        self.to_state = to_state


class MissingTransitionMetadataError(StateTransitionError):
    """Raised when metadata necessary for a transition is missing or incomplete."""

    def __init__(self, message: str) -> None:
        super().__init__("MISSING_TRANSITION_METADATA", message)


class ConcurrencyConflictError(StateTransitionError):
    """Raised when an update fails due to a version mismatch (optimistic locking)."""

    def __init__(self, message: str) -> None:
        super().__init__("CONCURRENCY_CONFLICT", message)
