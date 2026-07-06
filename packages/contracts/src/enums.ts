export enum DocumentStatus {
  DRAFT = "draft",
  UPLOADED = "uploaded",
  PARSING = "parsing",
  AI_EXTRACTED = "ai_extracted",
  IN_REVIEW = "in_review",
  CHANGES_REQUESTED = "changes_requested",
  REJECTED = "rejected",
  SCHOLAR_REVIEW = "scholar_review",
  SCHOLAR_APPROVED = "scholar_approved",
  PUBLISHED = "published",
  SUSPENDED = "suspended",
  ARCHIVED = "archived",
  NEW_VERSION = "new_version",
}

export enum ReviewDecision {
  APPROVE = "approve",
  REQUEST_CHANGES = "request_changes",
  REJECT = "reject",
  ESCALATE = "escalate",
  MARK_DUPLICATE = "mark_duplicate",
  MARK_LICENSE_ISSUE = "mark_license_issue",
}

export enum PermissionState {
  UNKNOWN = "unknown",
  ALLOWED = "allowed",
  PROHIBITED = "prohibited",
  CONDITIONAL = "conditional",
}

export enum EvidenceStatus {
  SUFFICIENT = "SUFFICIENT",
  PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT",
  INSUFFICIENT = "INSUFFICIENT",
  CONFLICTING = "CONFLICTING",
}

export enum RiskLevel {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  RESTRICTED = "restricted",
}

export enum IncidentSeverity {
  P0 = "p0",
  P1 = "p1",
  P2 = "p2",
  P3 = "p3",
}

export enum IncidentStatus {
  OPEN = "open",
  TRIAGED = "triaged",
  MITIGATED = "mitigated",
  RESOLVED = "resolved",
  CLOSED = "closed",
}

export enum ReviewTaskStatus {
  OPEN = "open",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
}

export enum ProviderStatus {
  ENABLED = "enabled",
  DISABLED = "disabled",
  DEGRADED = "degraded",
}
