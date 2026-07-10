"""Create private, sanitized evaluation-case candidates from confirmed incidents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from zayd_common.database.models import (
    AuditLog,
    EvaluationCase,
    EvaluationDataset,
    Incident,
    IncidentEvent,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

from .schema import EvaluationCaseContract, EvaluationVisibility, ReviewerStatus

INCIDENT_REGRESSION_POLICY_VERSION = "incident-regression-v1"
_CONFIRMED_INCIDENT_STATUSES = frozenset({"resolved", "closed"})
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?66|0)[ -]?(?:\d[ -]?){8,9}\d(?!\d)")
_THAI_ID_PATTERN = re.compile(r"(?<!\d)\d[ -]?\d{4}[ -]?\d{5}[ -]?\d{2}[ -]?\d(?!\d)")


class IncidentRegressionError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class IncidentRegressionResult:
    evaluation_case_id: UUID
    incident_id: UUID
    redaction_count: int
    schema_version: str
    policy_version: str


class IncidentRegressionService:
    """Creates a candidate without exposing incident payloads in the evaluation dataset."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        incident_id: UUID,
        dataset_id: UUID,
        contract: EvaluationCaseContract,
        *,
        actor_user_id: UUID,
        permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> IncidentRegressionResult:
        _require_permissions(permissions)
        _require_private_draft(contract)
        sanitized_contract, redaction_count = _sanitize_contract(contract)
        with self.uow:
            session = self._session()
            incident = session.get(Incident, incident_id)
            if incident is None:
                raise IncidentRegressionError(
                    "INCIDENT_REGRESSION_INCIDENT_NOT_FOUND",
                    "Incident was not found.",
                    status_code=404,
                )
            if incident.status not in _CONFIRMED_INCIDENT_STATUSES:
                raise IncidentRegressionError(
                    "INCIDENT_REGRESSION_NOT_CONFIRMED",
                    "Only resolved or closed incidents may create regression cases.",
                    status_code=409,
                )
            dataset = session.get(EvaluationDataset, dataset_id)
            if dataset is None:
                raise IncidentRegressionError(
                    "INCIDENT_REGRESSION_DATASET_NOT_FOUND",
                    "Evaluation dataset was not found.",
                    status_code=404,
                )
            if dataset.visibility != EvaluationVisibility.PRIVATE.value:
                raise IncidentRegressionError(
                    "INCIDENT_REGRESSION_DATASET_NOT_PRIVATE",
                    "Incident regression cases require a private dataset.",
                    status_code=409,
                )
            if session.scalar(
                select(EvaluationCase).where(
                    EvaluationCase.dataset_id == dataset_id,
                    EvaluationCase.case_key == sanitized_contract.case_key,
                )
            ):
                raise IncidentRegressionError(
                    "INCIDENT_REGRESSION_CASE_EXISTS",
                    "Case key already exists in dataset.",
                    status_code=409,
                )

            sources = [source.model_dump(mode="json") for source in sanitized_contract.sources]
            case = EvaluationCase(
                dataset_id=dataset_id,
                case_key=sanitized_contract.case_key,
                schema_version=sanitized_contract.schema_version,
                case_type=sanitized_contract.case_type.value,
                visibility=EvaluationVisibility.PRIVATE.value,
                reviewer_status=ReviewerStatus.DRAFT.value,
                reviewed_by=None,
                question=sanitized_contract.question,
                choices_json=[choice.model_dump() for choice in sanitized_contract.choices],
                expected_citations=[
                    {"citation_id": str(value)}
                    for value in sanitized_contract.expected_behavior.required_citation_ids
                ],
                expected_behavior=sanitized_contract.expected_behavior.model_dump(mode="json"),
                source_references=sources,
                license_metadata={
                    "sources": [
                        {
                            "source_id": item["source_id"],
                            "license_name": item["license_name"],
                            "license_status": item["license_status"],
                            "redistributable": item["redistributable"],
                        }
                        for item in sources
                    ]
                },
                provenance_json={
                    "origin": "incident_regression",
                    "incident_id": str(incident.id),
                    "incident_severity": incident.severity,
                    "incident_policy_version": incident.policy_version,
                    "regression_policy_version": INCIDENT_REGRESSION_POLICY_VERSION,
                },
                risk_level=sanitized_contract.risk_level,
            )
            session.add(case)
            session.flush()
            session.add(
                IncidentEvent(
                    incident_id=incident.id,
                    actor_user_id=actor_user_id,
                    event_type="regression_case_created",
                    status_from=None,
                    status_to=None,
                    details_json={
                        "evaluation_case_id": str(case.id),
                        "dataset_id": str(dataset.id),
                        "redaction_count": redaction_count,
                        "policy_version": INCIDENT_REGRESSION_POLICY_VERSION,
                    },
                    request_id=trace_id,
                )
            )
            session.add(
                AuditLog(
                    id=uuid4(),
                    actor_user_id=actor_user_id,
                    action="evaluation.incident_regression.create",
                    resource_type="evaluation_case",
                    resource_id=case.id,
                    outcome="success",
                    request_id=trace_id,
                    trace_id=trace_id,
                    before_summary={},
                    after_summary={
                        "incident_id": str(incident.id),
                        "dataset_id": str(dataset.id),
                        "case_key": case.case_key,
                        "schema_version": case.schema_version,
                        "redaction_count": redaction_count,
                        "policy_version": INCIDENT_REGRESSION_POLICY_VERSION,
                    },
                    source_context={},
                )
            )
            self.uow.commit()
            return IncidentRegressionResult(
                evaluation_case_id=case.id,
                incident_id=incident.id,
                redaction_count=redaction_count,
                schema_version=case.schema_version,
                policy_version=INCIDENT_REGRESSION_POLICY_VERSION,
            )

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _require_permissions(permissions: frozenset[str]) -> None:
    required = {Permission.FEEDBACK_MANAGE.value, Permission.EVALUATIONS_MANAGE.value}
    if not required.issubset(permissions):
        raise IncidentRegressionError(
            "INCIDENT_REGRESSION_FORBIDDEN", "Forbidden.", status_code=403
        )


def _require_private_draft(contract: EvaluationCaseContract) -> None:
    if (
        contract.visibility != EvaluationVisibility.PRIVATE
        or contract.reviewer_status != ReviewerStatus.DRAFT
    ):
        raise IncidentRegressionError(
            "INCIDENT_REGRESSION_CASE_STATE_INVALID",
            "Incident regression cases must be created as private drafts.",
        )
    if contract.reviewed_by is not None:
        raise IncidentRegressionError(
            "INCIDENT_REGRESSION_CASE_STATE_INVALID",
            "Incident regression candidates may not set reviewed_by.",
        )


def _sanitize_contract(contract: EvaluationCaseContract) -> tuple[EvaluationCaseContract, int]:
    payload = contract.model_dump(mode="json")
    question, redaction_count = _redact_text(payload["question"])
    payload["question"] = question
    choices, choice_count = _redact_value(payload["choices"])
    expected_behavior, behavior_count = _redact_value(payload["expected_behavior"])
    sources, source_count = _sanitize_sources(payload["sources"])
    payload["choices"] = choices
    payload["expected_behavior"] = expected_behavior
    payload["sources"] = sources
    payload["provenance"] = {}
    return EvaluationCaseContract.model_validate(payload), (
        redaction_count + choice_count + behavior_count + source_count
    )


def _sanitize_sources(sources: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    sanitized: list[dict[str, Any]] = []
    count = 0
    for source in sources:
        item = dict(source)
        for key in ("canonical_reference", "license_name", "license_status"):
            item[key], found = _redact_text(item[key])
            count += found
        sanitized.append(item)
    return sanitized, count


def _redact_value(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        list_redactions = [_redact_value(item) for item in value]
        return [item for item, _ in list_redactions], sum(count for _, count in list_redactions)
    if isinstance(value, dict):
        dict_redactions = {key: _redact_value(item) for key, item in value.items()}
        return (
            {key: item for key, (item, _) in dict_redactions.items()},
            sum(count for _, count in dict_redactions.values()),
        )
    return value, 0


def _redact_text(text: str) -> tuple[str, int]:
    result, count = _EMAIL_PATTERN.subn("[REDACTED_EMAIL]", text)
    result, phone_count = _PHONE_PATTERN.subn("[REDACTED_PHONE]", result)
    result, thai_id_count = _THAI_ID_PATTERN.subn("[REDACTED_THAI_ID]", result)
    return result, count + phone_count + thai_id_count
