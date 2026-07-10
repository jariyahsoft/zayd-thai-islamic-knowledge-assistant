"""Versioned deterministic contracts for Zayd evaluation cases."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

EVALUATION_CASE_SCHEMA_VERSION: Literal["evaluation-case-v1"] = "evaluation-case-v1"


class EvaluationCaseType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    OPEN_ENDED = "open_ended"
    RETRIEVAL_ONLY = "retrieval_only"
    CITATION = "citation"
    ABSTENTION = "abstention"
    RISK_ROUTING = "risk_routing"


class EvaluationVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class ReviewerStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class Choice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    key: str = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1, max_length=1000)


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: UUID
    citation_id: UUID | None = None
    canonical_reference: str = Field(min_length=1, max_length=500)
    license_name: str = Field(min_length=1, max_length=200)
    license_status: str = Field(min_length=1, max_length=50)
    redistributable: bool


class ExpectedBehavior(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    outcome: Literal["answer", "abstain", "route_high_risk", "retrieve", "cite"]
    expected_choice_keys: tuple[str, ...] = ()
    required_source_ids: tuple[UUID, ...] = ()
    required_citation_ids: tuple[UUID, ...] = ()
    rubric: dict[str, Any] = Field(default_factory=dict)


class EvaluationCaseContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["evaluation-case-v1"] = EVALUATION_CASE_SCHEMA_VERSION
    case_key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,127}$")
    case_type: EvaluationCaseType
    visibility: EvaluationVisibility
    reviewer_status: ReviewerStatus
    reviewed_by: UUID | None = None
    question: str = Field(min_length=1, max_length=8000)
    choices: tuple[Choice, ...] = ()
    expected_behavior: ExpectedBehavior
    sources: tuple[SourceReference, ...] = Field(min_length=1)
    risk_level: Literal["low", "medium", "high", "restricted"] = "low"
    provenance: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_case_rules(self) -> EvaluationCaseContract:
        keys = [choice.key for choice in self.choices]
        if len(keys) != len(set(keys)):
            raise ValueError("choice keys must be unique")
        if self.case_type == EvaluationCaseType.MULTIPLE_CHOICE:
            if len(self.choices) < 2 or not self.expected_behavior.expected_choice_keys:
                raise ValueError("multiple_choice cases require choices and expected choice keys")
            if not set(self.expected_behavior.expected_choice_keys).issubset(keys):
                raise ValueError("expected choice keys must exist in choices")
        elif self.choices:
            raise ValueError("choices are only valid for multiple_choice cases")
        required_outcome = {
            EvaluationCaseType.RETRIEVAL_ONLY: "retrieve",
            EvaluationCaseType.CITATION: "cite",
            EvaluationCaseType.ABSTENTION: "abstain",
            EvaluationCaseType.RISK_ROUTING: "route_high_risk",
        }.get(self.case_type)
        if required_outcome and self.expected_behavior.outcome != required_outcome:
            raise ValueError(f"{self.case_type.value} requires outcome {required_outcome}")
        if (
            self.reviewer_status in {ReviewerStatus.REVIEWED, ReviewerStatus.APPROVED}
            and not self.reviewed_by
        ):
            raise ValueError("reviewed cases require reviewed_by")
        if self.visibility == EvaluationVisibility.PUBLIC:
            if self.reviewer_status != ReviewerStatus.APPROVED:
                raise ValueError("public cases must be approved")
            if any(not source.redistributable for source in self.sources):
                raise ValueError("public cases require redistributable sources")
        return self
