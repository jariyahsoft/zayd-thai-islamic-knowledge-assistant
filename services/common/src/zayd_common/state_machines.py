from datetime import UTC, datetime
from typing import Any, ClassVar, cast

from pydantic import BaseModel, Field

from zayd_common.enums import DocumentStatus, IncidentStatus, ReviewTaskStatus
from zayd_common.exceptions import InvalidStateTransitionError, MissingTransitionMetadataError


class TransitionMetadata(BaseModel):
    """Metadata recorded with every state transition for auditing and compliance."""

    actor_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the actor performing the transition",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of when the transition occurred",
    )
    reason: str | None = Field(
        default=None,
        description="Detailed reason for the transition, required for sensitive states",
    )
    notes: str | None = Field(
        default=None,
        description="Optional additional notes or context",
    )


class BaseStateMachine[T]:
    """Generic base class for status lifecycle and state transition rules."""

    TRANSITIONS: ClassVar[dict[Any, set[Any]]] = {}
    ERROR_CODE: ClassVar[str] = "INVALID_TRANSITION"

    @classmethod
    def can_transition(cls, from_state: T, to_state: T) -> bool:
        """Return whether a transition from from_state to to_state is allowed."""
        return to_state in cls.TRANSITIONS.get(from_state, set())

    @classmethod
    def get_allowed_transitions(cls, from_state: T) -> set[T]:
        """Return the set of all allowed states transitioning from from_state."""
        return cast(set[T], cls.TRANSITIONS.get(from_state, set()))

    @classmethod
    def is_terminal(cls, state: T) -> bool:
        """Return True if the state has no outgoing transitions."""
        return not cls.get_allowed_transitions(state)

    @classmethod
    def validate_transition(cls, from_state: T, to_state: T, metadata: TransitionMetadata) -> None:
        """Validate if transition is allowed and metadata is complete.

        Raises InvalidStateTransitionError or MissingTransitionMetadataError.
        """
        if not cls.can_transition(from_state, to_state):
            raise InvalidStateTransitionError(cls.ERROR_CODE, str(from_state), str(to_state))

        if not metadata.actor_id or not metadata.actor_id.strip():
            raise MissingTransitionMetadataError("Actor ID is required for state transition.")

        if not metadata.timestamp:
            raise MissingTransitionMetadataError("Timestamp is required for state transition.")


class DocumentStateMachine(BaseStateMachine[DocumentStatus]):
    """State machine governing Document status lifecycles."""

    ERROR_CODE: ClassVar[str] = "DOCUMENT_INVALID_TRANSITION"
    TRANSITIONS: ClassVar[dict[DocumentStatus, set[DocumentStatus]]] = {
        DocumentStatus.DRAFT: {DocumentStatus.UPLOADED},
        DocumentStatus.UPLOADED: {DocumentStatus.PARSING},
        DocumentStatus.PARSING: {DocumentStatus.AI_EXTRACTED, DocumentStatus.REJECTED},
        DocumentStatus.AI_EXTRACTED: {DocumentStatus.IN_REVIEW},
        DocumentStatus.IN_REVIEW: {
            DocumentStatus.CHANGES_REQUESTED,
            DocumentStatus.REJECTED,
            DocumentStatus.SCHOLAR_REVIEW,
        },
        DocumentStatus.CHANGES_REQUESTED: {DocumentStatus.IN_REVIEW},
        DocumentStatus.SCHOLAR_REVIEW: {
            DocumentStatus.CHANGES_REQUESTED,
            DocumentStatus.REJECTED,
            DocumentStatus.SCHOLAR_APPROVED,
        },
        DocumentStatus.SCHOLAR_APPROVED: {DocumentStatus.PUBLISHED},
        DocumentStatus.PUBLISHED: {
            DocumentStatus.SUSPENDED,
            DocumentStatus.ARCHIVED,
            DocumentStatus.NEW_VERSION,
        },
        DocumentStatus.SUSPENDED: {
            DocumentStatus.PUBLISHED,
            DocumentStatus.ARCHIVED,
            DocumentStatus.NEW_VERSION,
        },
        DocumentStatus.ARCHIVED: set(),
        DocumentStatus.REJECTED: set(),
        DocumentStatus.NEW_VERSION: set(),
    }

    @classmethod
    def validate_transition(
        cls,
        from_state: DocumentStatus,
        to_state: DocumentStatus,
        metadata: TransitionMetadata,
    ) -> None:
        super().validate_transition(from_state, to_state, metadata)

        # Transition to published, suspended, or rejected requires non-empty reason
        if to_state in (
            DocumentStatus.PUBLISHED,
            DocumentStatus.SUSPENDED,
            DocumentStatus.REJECTED,
        ):
            if not metadata.reason or not metadata.reason.strip():
                raise MissingTransitionMetadataError(
                    f"A non-empty reason is required to transition to '{to_state}' status."
                )


class ReviewTaskStateMachine(BaseStateMachine[ReviewTaskStatus]):
    """State machine governing Review Task status lifecycles."""

    ERROR_CODE: ClassVar[str] = "REVIEW_TASK_INVALID_TRANSITION"
    TRANSITIONS: ClassVar[dict[ReviewTaskStatus, set[ReviewTaskStatus]]] = {
        ReviewTaskStatus.OPEN: {
            ReviewTaskStatus.IN_PROGRESS,
            ReviewTaskStatus.COMPLETED,
            ReviewTaskStatus.CANCELLED,
        },
        ReviewTaskStatus.IN_PROGRESS: {
            ReviewTaskStatus.COMPLETED,
            ReviewTaskStatus.CANCELLED,
        },
        ReviewTaskStatus.COMPLETED: set(),
        ReviewTaskStatus.CANCELLED: set(),
    }


class IncidentStateMachine(BaseStateMachine[IncidentStatus]):
    """State machine governing Incident status lifecycles."""

    ERROR_CODE: ClassVar[str] = "INCIDENT_INVALID_TRANSITION"
    TRANSITIONS: ClassVar[dict[IncidentStatus, set[IncidentStatus]]] = {
        IncidentStatus.OPEN: {IncidentStatus.TRIAGED, IncidentStatus.CLOSED},
        IncidentStatus.TRIAGED: {IncidentStatus.MITIGATED, IncidentStatus.CLOSED},
        IncidentStatus.MITIGATED: {IncidentStatus.RESOLVED, IncidentStatus.CLOSED},
        IncidentStatus.RESOLVED: {IncidentStatus.CLOSED},
        IncidentStatus.CLOSED: {IncidentStatus.OPEN},
    }
