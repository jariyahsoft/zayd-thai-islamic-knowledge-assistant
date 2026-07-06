from enum import StrEnum


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    AI_EXTRACTED = "ai_extracted"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    SCHOLAR_REVIEW = "scholar_review"
    SCHOLAR_APPROVED = "scholar_approved"
    PUBLISHED = "published"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    NEW_VERSION = "new_version"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"
    ESCALATE = "escalate"
    MARK_DUPLICATE = "mark_duplicate"
    MARK_LICENSE_ISSUE = "mark_license_issue"


class PermissionState(StrEnum):
    UNKNOWN = "unknown"
    ALLOWED = "allowed"
    PROHIBITED = "prohibited"
    CONDITIONAL = "conditional"


class EvidenceStatus(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    RESTRICTED = "restricted"


class IncidentSeverity(StrEnum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class IncidentStatus(StrEnum):
    OPEN = "open"
    TRIAGED = "triaged"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ReviewTaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProviderStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEGRADED = "degraded"
