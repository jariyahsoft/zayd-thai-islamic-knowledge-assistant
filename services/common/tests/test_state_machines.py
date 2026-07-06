from datetime import UTC, datetime

import pytest
from zayd_common.enums import DocumentStatus, IncidentStatus, ReviewTaskStatus
from zayd_common.exceptions import InvalidStateTransitionError, MissingTransitionMetadataError
from zayd_common.state_machines import (
    DocumentStateMachine,
    IncidentStateMachine,
    ReviewTaskStateMachine,
    TransitionMetadata,
)


def test_transition_metadata_validation() -> None:
    # Valid metadata
    metadata = TransitionMetadata(actor_id="user-123", timestamp=datetime.now(UTC))
    assert metadata.actor_id == "user-123"
    assert metadata.reason is None


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (DocumentStatus.DRAFT, DocumentStatus.UPLOADED),
        (DocumentStatus.UPLOADED, DocumentStatus.PARSING),
        (DocumentStatus.PARSING, DocumentStatus.AI_EXTRACTED),
        (DocumentStatus.PARSING, DocumentStatus.REJECTED),
        (DocumentStatus.AI_EXTRACTED, DocumentStatus.IN_REVIEW),
        (DocumentStatus.IN_REVIEW, DocumentStatus.SCHOLAR_REVIEW),
        (DocumentStatus.IN_REVIEW, DocumentStatus.CHANGES_REQUESTED),
        (DocumentStatus.IN_REVIEW, DocumentStatus.REJECTED),
        (DocumentStatus.CHANGES_REQUESTED, DocumentStatus.IN_REVIEW),
        (DocumentStatus.SCHOLAR_REVIEW, DocumentStatus.SCHOLAR_APPROVED),
        (DocumentStatus.SCHOLAR_REVIEW, DocumentStatus.CHANGES_REQUESTED),
        (DocumentStatus.SCHOLAR_REVIEW, DocumentStatus.REJECTED),
        (DocumentStatus.SCHOLAR_APPROVED, DocumentStatus.PUBLISHED),
        (DocumentStatus.PUBLISHED, DocumentStatus.SUSPENDED),
        (DocumentStatus.PUBLISHED, DocumentStatus.ARCHIVED),
        (DocumentStatus.PUBLISHED, DocumentStatus.NEW_VERSION),
        (DocumentStatus.SUSPENDED, DocumentStatus.PUBLISHED),
        (DocumentStatus.SUSPENDED, DocumentStatus.ARCHIVED),
        (DocumentStatus.SUSPENDED, DocumentStatus.NEW_VERSION),
    ],
)
def test_document_state_machine_valid_transitions(
    from_state: DocumentStatus, to_state: DocumentStatus
) -> None:
    metadata = TransitionMetadata(
        actor_id="agent-0",
        timestamp=datetime.now(UTC),
        reason="Proceeding through lifecycle",
    )
    assert DocumentStateMachine.can_transition(from_state, to_state) is True
    # Should not raise any exception
    DocumentStateMachine.validate_transition(from_state, to_state, metadata)


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (DocumentStatus.DRAFT, DocumentStatus.PUBLISHED),
        (DocumentStatus.UPLOADED, DocumentStatus.PUBLISHED),
        (DocumentStatus.AI_EXTRACTED, DocumentStatus.PUBLISHED),
        (DocumentStatus.ARCHIVED, DocumentStatus.DRAFT),
        (DocumentStatus.REJECTED, DocumentStatus.IN_REVIEW),
        (DocumentStatus.NEW_VERSION, DocumentStatus.PUBLISHED),
    ],
)
def test_document_state_machine_invalid_transitions(
    from_state: DocumentStatus, to_state: DocumentStatus
) -> None:
    metadata = TransitionMetadata(actor_id="agent-0", timestamp=datetime.now(UTC), reason="Invalid")
    assert DocumentStateMachine.can_transition(from_state, to_state) is False

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        DocumentStateMachine.validate_transition(from_state, to_state, metadata)

    assert exc_info.value.error_code == "DOCUMENT_INVALID_TRANSITION"
    assert exc_info.value.from_state == from_state
    assert exc_info.value.to_state == to_state


@pytest.mark.parametrize(
    "target_state",
    [
        DocumentStatus.PUBLISHED,
        DocumentStatus.SUSPENDED,
        DocumentStatus.REJECTED,
    ],
)
def test_document_state_machine_requires_reason(target_state: DocumentStatus) -> None:
    # Find a valid source state for this target state
    source_state = None
    for state, allowed in DocumentStateMachine.TRANSITIONS.items():
        if target_state in allowed:
            source_state = state
            break

    assert source_state is not None

    # Empty reason
    metadata_no_reason = TransitionMetadata(
        actor_id="agent-0", timestamp=datetime.now(UTC), reason=""
    )
    with pytest.raises(MissingTransitionMetadataError) as exc_info:
        DocumentStateMachine.validate_transition(source_state, target_state, metadata_no_reason)
    assert "reason is required" in str(exc_info.value)

    # Missing reason (None)
    metadata_none_reason = TransitionMetadata(
        actor_id="agent-0", timestamp=datetime.now(UTC), reason=None
    )
    with pytest.raises(MissingTransitionMetadataError) as exc_info:
        DocumentStateMachine.validate_transition(source_state, target_state, metadata_none_reason)
    assert "reason is required" in str(exc_info.value)

    # Valid reason
    metadata_ok = TransitionMetadata(
        actor_id="agent-0", timestamp=datetime.now(UTC), reason="Valid reason"
    )
    DocumentStateMachine.validate_transition(source_state, target_state, metadata_ok)


def test_document_terminal_states() -> None:
    assert DocumentStateMachine.is_terminal(DocumentStatus.ARCHIVED) is True
    assert DocumentStateMachine.is_terminal(DocumentStatus.REJECTED) is True
    assert DocumentStateMachine.is_terminal(DocumentStatus.NEW_VERSION) is True
    assert DocumentStateMachine.is_terminal(DocumentStatus.DRAFT) is False


def test_review_task_state_machine() -> None:
    metadata = TransitionMetadata(actor_id="r-1", timestamp=datetime.now(UTC))
    assert (
        ReviewTaskStateMachine.can_transition(ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_PROGRESS)
        is True
    )
    assert (
        ReviewTaskStateMachine.can_transition(ReviewTaskStatus.OPEN, ReviewTaskStatus.COMPLETED)
        is True
    )
    assert (
        ReviewTaskStateMachine.can_transition(
            ReviewTaskStatus.IN_PROGRESS, ReviewTaskStatus.COMPLETED
        )
        is True
    )
    assert (
        ReviewTaskStateMachine.can_transition(ReviewTaskStatus.COMPLETED, ReviewTaskStatus.OPEN)
        is False
    )

    ReviewTaskStateMachine.validate_transition(
        ReviewTaskStatus.OPEN, ReviewTaskStatus.IN_PROGRESS, metadata
    )

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        ReviewTaskStateMachine.validate_transition(
            ReviewTaskStatus.COMPLETED, ReviewTaskStatus.IN_PROGRESS, metadata
        )
    assert exc_info.value.error_code == "REVIEW_TASK_INVALID_TRANSITION"


def test_incident_state_machine() -> None:
    metadata = TransitionMetadata(actor_id="i-1", timestamp=datetime.now(UTC))
    assert IncidentStateMachine.can_transition(IncidentStatus.OPEN, IncidentStatus.TRIAGED) is True
    assert (
        IncidentStateMachine.can_transition(IncidentStatus.TRIAGED, IncidentStatus.MITIGATED)
        is True
    )
    assert (
        IncidentStateMachine.can_transition(IncidentStatus.MITIGATED, IncidentStatus.RESOLVED)
        is True
    )
    assert (
        IncidentStateMachine.can_transition(IncidentStatus.RESOLVED, IncidentStatus.CLOSED) is True
    )
    assert (
        IncidentStateMachine.can_transition(IncidentStatus.CLOSED, IncidentStatus.OPEN) is True
    )  # Reopen

    IncidentStateMachine.validate_transition(IncidentStatus.OPEN, IncidentStatus.TRIAGED, metadata)

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        IncidentStateMachine.validate_transition(
            IncidentStatus.RESOLVED, IncidentStatus.MITIGATED, metadata
        )
    assert exc_info.value.error_code == "INCIDENT_INVALID_TRANSITION"
