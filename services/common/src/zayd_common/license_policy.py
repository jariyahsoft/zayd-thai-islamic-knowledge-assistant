"""Deterministic license policy engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

LicensePolicyWorkflow = Literal["ingestion", "retrieval", "export"]
LicensePolicyAction = Literal[
    "persistent_storage",
    "cache",
    "embedding",
    "commercial_use",
    "redistribution",
    "attribution",
]

LICENSE_POLICY_ENGINE_VERSION = "license-policy-engine-v1"
EPHEMERAL_CACHE_TTL_SECONDS = 86_400
PERSISTENT_CACHE_TTL_SECONDS = 604_800
POLICY_WORKFLOWS = {"ingestion", "retrieval", "export"}
PERSISTENT_STATUSES = {"persistent_private", "persistent_redistributable"}
REDISTRIBUTABLE_STATUSES = {"persistent_redistributable"}
BLOCKING_STATUSES = {"unknown", "prohibited", "expired"}
ALLOWING_PERMISSION_STATES = {"allowed", "conditional"}

WORKFLOW_REQUIRED_ACTIONS: dict[str, tuple[LicensePolicyAction, ...]] = {
    "ingestion": ("persistent_storage", "attribution"),
    "retrieval": ("persistent_storage", "embedding", "attribution"),
    "export": ("redistribution", "commercial_use", "attribution"),
}


@dataclass(frozen=True)
class LicensePolicyInput:
    license_id: UUID
    source_id: UUID
    license_version: str | None
    status: str
    storage_permission: str
    embedding_permission: str
    commercial_use: str
    redistribution: str
    attribution_required: bool
    attribution_template: str | None
    valid_from: date | None
    valid_until: date | None


@dataclass(frozen=True)
class LicenseActionDecision:
    action: LicensePolicyAction
    allowed: bool
    reason_codes: tuple[str, ...]
    source_license_version: str | None
    max_cache_ttl_seconds: int | None = None
    attribution_required: bool | None = None
    attribution_template: str | None = None


@dataclass(frozen=True)
class LicensePolicyDecision:
    license_id: UUID
    source_id: UUID
    workflow: str
    policy_version: str
    evaluated_on: date
    source_license_version: str | None
    workflow_allowed: bool
    llm_override_allowed: bool
    reason_codes: tuple[str, ...]
    actions: tuple[LicenseActionDecision, ...]


def evaluate_license_policy(
    license_record: LicensePolicyInput,
    *,
    workflow: str,
    today: date | None = None,
) -> LicensePolicyDecision:
    """Evaluate all license actions for a workflow using deterministic rules."""
    evaluation_date = today or datetime.now(UTC).date()
    action_decisions = (
        _persistent_storage_decision(license_record, evaluation_date),
        _cache_decision(license_record, evaluation_date),
        _embedding_decision(license_record, evaluation_date),
        _commercial_use_decision(license_record, evaluation_date),
        _redistribution_decision(license_record, evaluation_date),
        _attribution_decision(license_record),
    )
    workflow_required_actions = WORKFLOW_REQUIRED_ACTIONS.get(workflow, ())
    workflow_allowed = bool(workflow_required_actions) and all(
        decision.allowed
        for decision in action_decisions
        if decision.action in workflow_required_actions
    )
    reason_codes = _deduplicate(
        (
            "WORKFLOW_ALLOWED"
            if workflow_allowed
            else f"WORKFLOW_{workflow.upper()}_DENIED"
            if workflow in POLICY_WORKFLOWS
            else "WORKFLOW_INVALID"
        ),
        *(code for decision in action_decisions for code in decision.reason_codes),
    )
    return LicensePolicyDecision(
        license_id=license_record.license_id,
        source_id=license_record.source_id,
        workflow=workflow,
        policy_version=LICENSE_POLICY_ENGINE_VERSION,
        evaluated_on=evaluation_date,
        source_license_version=license_record.license_version,
        workflow_allowed=workflow_allowed,
        llm_override_allowed=False,
        reason_codes=reason_codes,
        actions=action_decisions,
    )


def _persistent_storage_decision(
    license_record: LicensePolicyInput,
    evaluation_date: date,
) -> LicenseActionDecision:
    blocker = _global_blocker(license_record, evaluation_date)
    if blocker is not None:
        return _decision(license_record, "persistent_storage", False, blocker)
    if license_record.status not in PERSISTENT_STATUSES:
        return _decision(
            license_record,
            "persistent_storage",
            False,
            "STATUS_DOES_NOT_ALLOW_PERSISTENT_STORAGE",
        )
    if license_record.storage_permission not in ALLOWING_PERMISSION_STATES:
        return _decision(license_record, "persistent_storage", False, "STORAGE_PERMISSION_DENIED")
    permission_reason = _permission_reason("STORAGE", license_record.storage_permission)
    return _decision(license_record, "persistent_storage", True, permission_reason)


def _cache_decision(
    license_record: LicensePolicyInput,
    evaluation_date: date,
) -> LicenseActionDecision:
    blocker = _global_blocker(license_record, evaluation_date)
    if blocker is not None:
        return _decision(license_record, "cache", False, blocker, max_cache_ttl_seconds=0)
    if license_record.status in {"review_required", "ephemeral_cache_only"}:
        return _decision(
            license_record,
            "cache",
            True,
            "CACHE_ALLOWED_LIMITED_TTL",
            max_cache_ttl_seconds=EPHEMERAL_CACHE_TTL_SECONDS,
        )
    if license_record.status in PERSISTENT_STATUSES:
        return _decision(
            license_record,
            "cache",
            True,
            "CACHE_ALLOWED_PERSISTENT_LICENSE",
            max_cache_ttl_seconds=PERSISTENT_CACHE_TTL_SECONDS,
        )
    return _decision(
        license_record,
        "cache",
        False,
        "CACHE_DENIED_STATUS",
        max_cache_ttl_seconds=0,
    )


def _embedding_decision(
    license_record: LicensePolicyInput,
    evaluation_date: date,
) -> LicenseActionDecision:
    blocker = _global_blocker(license_record, evaluation_date)
    if blocker is not None:
        return _decision(license_record, "embedding", False, blocker)
    if license_record.status not in PERSISTENT_STATUSES:
        return _decision(license_record, "embedding", False, "STATUS_DOES_NOT_ALLOW_EMBEDDING")
    if license_record.storage_permission not in ALLOWING_PERMISSION_STATES:
        return _decision(license_record, "embedding", False, "STORAGE_PERMISSION_DENIED")
    if license_record.embedding_permission not in ALLOWING_PERMISSION_STATES:
        return _decision(license_record, "embedding", False, "EMBEDDING_PERMISSION_DENIED")
    return _decision(
        license_record,
        "embedding",
        True,
        _permission_reason("EMBEDDING", license_record.embedding_permission),
    )


def _commercial_use_decision(
    license_record: LicensePolicyInput,
    evaluation_date: date,
) -> LicenseActionDecision:
    blocker = _global_blocker(license_record, evaluation_date)
    if blocker is not None:
        return _decision(license_record, "commercial_use", False, blocker)
    if license_record.status not in PERSISTENT_STATUSES:
        return _decision(
            license_record,
            "commercial_use",
            False,
            "STATUS_DOES_NOT_ALLOW_COMMERCIAL_USE",
        )
    if license_record.commercial_use not in ALLOWING_PERMISSION_STATES:
        return _decision(license_record, "commercial_use", False, "COMMERCIAL_USE_DENIED")
    return _decision(
        license_record,
        "commercial_use",
        True,
        _permission_reason("COMMERCIAL_USE", license_record.commercial_use),
    )


def _redistribution_decision(
    license_record: LicensePolicyInput,
    evaluation_date: date,
) -> LicenseActionDecision:
    blocker = _global_blocker(license_record, evaluation_date)
    if blocker is not None:
        return _decision(license_record, "redistribution", False, blocker)
    if license_record.status not in REDISTRIBUTABLE_STATUSES:
        return _decision(
            license_record,
            "redistribution",
            False,
            "STATUS_DOES_NOT_ALLOW_REDISTRIBUTION",
        )
    if license_record.redistribution not in ALLOWING_PERMISSION_STATES:
        return _decision(license_record, "redistribution", False, "REDISTRIBUTION_DENIED")
    return _decision(
        license_record,
        "redistribution",
        True,
        _permission_reason("REDISTRIBUTION", license_record.redistribution),
    )


def _attribution_decision(license_record: LicensePolicyInput) -> LicenseActionDecision:
    if not license_record.attribution_required:
        return _decision(
            license_record,
            "attribution",
            True,
            "ATTRIBUTION_NOT_REQUIRED",
            attribution_required=False,
        )
    if not license_record.attribution_template:
        return _decision(
            license_record,
            "attribution",
            False,
            "ATTRIBUTION_TEMPLATE_MISSING",
            attribution_required=True,
        )
    return _decision(
        license_record,
        "attribution",
        True,
        "ATTRIBUTION_REQUIRED",
        attribution_required=True,
        attribution_template=license_record.attribution_template,
    )


def _global_blocker(license_record: LicensePolicyInput, evaluation_date: date) -> str | None:
    if license_record.status == "unknown":
        return "LICENSE_STATUS_UNKNOWN"
    if license_record.status == "prohibited":
        return "LICENSE_STATUS_PROHIBITED"
    if license_record.status == "expired":
        return "LICENSE_STATUS_EXPIRED"
    if license_record.valid_from is not None and license_record.valid_from > evaluation_date:
        return "LICENSE_NOT_YET_VALID"
    if license_record.valid_until is not None and license_record.valid_until < evaluation_date:
        return "LICENSE_DATE_EXPIRED"
    return None


def _permission_reason(prefix: str, permission: str) -> str:
    if permission == "conditional":
        return f"{prefix}_PERMISSION_CONDITIONAL"
    return f"{prefix}_PERMISSION_ALLOWED"


def _decision(
    license_record: LicensePolicyInput,
    action: LicensePolicyAction,
    allowed: bool,
    *reason_codes: str,
    max_cache_ttl_seconds: int | None = None,
    attribution_required: bool | None = None,
    attribution_template: str | None = None,
) -> LicenseActionDecision:
    return LicenseActionDecision(
        action=action,
        allowed=allowed,
        reason_codes=_deduplicate(*reason_codes),
        source_license_version=license_record.license_version,
        max_cache_ttl_seconds=max_cache_ttl_seconds,
        attribution_required=attribution_required,
        attribution_template=attribution_template,
    )


def _deduplicate(*values: str) -> tuple[str, ...]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return tuple(ordered)
