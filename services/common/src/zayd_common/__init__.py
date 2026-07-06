"""Shared Python foundations for Zayd services."""

from .database import (
    AbstractDocumentRepository,
    AbstractIncidentRepository,
    AbstractSourceRepository,
    AbstractUnitOfWork,
    AbstractUserRepository,
    Base,
    SQLAlchemyDocumentRepository,
    SQLAlchemyIncidentRepository,
    SQLAlchemySourceRepository,
    SQLAlchemyUnitOfWork,
    SQLAlchemyUserRepository,
    get_sessionmaker,
)
from .enums import (
    DocumentStatus,
    EvidenceStatus,
    IncidentSeverity,
    IncidentStatus,
    PermissionState,
    ProviderStatus,
    ReviewDecision,
    ReviewTaskStatus,
    RiskLevel,
)
from .exceptions import (
    ConcurrencyConflictError,
    InvalidStateTransitionError,
    MissingTransitionMetadataError,
    StateTransitionError,
)
from .health import HealthStatus
from .logging import get_logger
from .retrievability import can_activate_embedding, is_document_retrievable
from .settings import ServiceSettings
from .state_machines import (
    DocumentStateMachine,
    IncidentStateMachine,
    ReviewTaskStateMachine,
    TransitionMetadata,
)

__all__ = [
    "HealthStatus",
    "ServiceSettings",
    "get_logger",
    "DocumentStatus",
    "ReviewDecision",
    "PermissionState",
    "EvidenceStatus",
    "RiskLevel",
    "IncidentSeverity",
    "IncidentStatus",
    "ReviewTaskStatus",
    "ProviderStatus",
    "StateTransitionError",
    "InvalidStateTransitionError",
    "MissingTransitionMetadataError",
    "ConcurrencyConflictError",
    "TransitionMetadata",
    "DocumentStateMachine",
    "ReviewTaskStateMachine",
    "IncidentStateMachine",
    "is_document_retrievable",
    "can_activate_embedding",
    "Base",
    "AbstractUserRepository",
    "SQLAlchemyUserRepository",
    "AbstractSourceRepository",
    "SQLAlchemySourceRepository",
    "AbstractDocumentRepository",
    "SQLAlchemyDocumentRepository",
    "AbstractIncidentRepository",
    "SQLAlchemyIncidentRepository",
    "AbstractUnitOfWork",
    "SQLAlchemyUnitOfWork",
    "get_sessionmaker",
]
