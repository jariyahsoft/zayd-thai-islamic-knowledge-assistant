"""Prompt and policy registry services for governed configuration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.database.models import (
    AuditLog,
    ModelConfiguration,
    PolicyVersion,
    PromptVersion,
    Provider,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

PROMPT_REGISTRY_VERSION = "prompt-registry-v1"
DEFAULT_POLICY_VERSION = "v1"
DEFAULT_ANSWER_PROMPT_NAME = "answer-generation"
DEFAULT_ANSWER_PROMPT_VERSION = "v1"

PromptRegistryErrorCode = Literal[
    "PROMPT_NOT_FOUND",
    "PROMPT_NAME_REQUIRED",
    "PROMPT_VERSION_REQUIRED",
    "PROMPT_BODY_REQUIRED",
    "PROMPT_SCHEMA_REQUIRED",
    "PROMPT_OWNER_REQUIRED",
    "PROMPT_STATUS_INVALID",
    "PROMPT_APPROVAL_FORBIDDEN",
    "PROMPT_ACTIVE_NOT_FOUND",
    "PROMPT_APPROVED_VERSION_REQUIRED",
    "PROMPT_MODEL_CONFIGURATION_REQUIRED",
    "PROMPT_COMPARE_INPUT_INVALID",
    "PROMPT_ROLLBACK_TARGET_INVALID",
    "POLICY_NOT_FOUND",
]

PROMPT_STATUSES = {"draft", "approved", "deprecated", "archived"}
PROMPT_ROLLBACK_ALLOWED = {"approved", "deprecated"}


class PromptRegistryError(Exception):
    """Stable prompt registry error."""

    def __init__(
        self,
        code: PromptRegistryErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class PromptTestCase:
    name: str
    input_payload: dict[str, Any]
    expected_assertions: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input_payload": self.input_payload,
            "expected_assertions": list(self.expected_assertions),
        }


@dataclass(frozen=True)
class PromptDefinition:
    id: UUID
    name: str
    version: str
    prompt_body: str
    status: str
    owner: str
    purpose: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    changelog: tuple[str, ...]
    test_cases: tuple[PromptTestCase, ...]
    prompt_hash: str
    created_by: UUID
    approved_by: UUID | None
    created_at: datetime
    updated_at: datetime
    active: bool
    registry_version: str = PROMPT_REGISTRY_VERSION


@dataclass(frozen=True)
class PromptCreate:
    name: str
    version: str
    prompt_body: str
    purpose: str
    owner: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    changelog: tuple[str, ...] = ()
    test_cases: tuple[PromptTestCase, ...] = ()
    status: str = "draft"


@dataclass(frozen=True)
class PromptStatusChange:
    prompt: PromptDefinition
    active_prompt: PromptDefinition | None
    changed: bool
    trace: dict[str, Any]


@dataclass(frozen=True)
class PromptComparison:
    prompt_name: str
    from_version: str
    to_version: str
    from_status: str
    to_status: str
    from_hash: str
    to_hash: str
    body_changed: bool
    purpose_changed: bool
    owner_changed: bool
    input_schema_changed: bool
    output_schema_changed: bool
    changelog_added: tuple[str, ...]
    test_case_names_added: tuple[str, ...]
    trace: dict[str, Any]


class PromptRegistryService:
    """Manage governed prompt and policy version records."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def create_prompt(
        self,
        *,
        data: PromptCreate,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> PromptDefinition:
        normalized = _normalize_prompt_create(data)
        with self.uow:
            existing = self.uow.prompts.get_prompt_by_name_version(normalized.name, normalized.version)
            if existing is not None:
                raise PromptRegistryError(
                    "PROMPT_VERSION_REQUIRED",
                    "Prompt name/version already exists.",
                    status_code=409,
                )
            draft = PromptCreate(
                name=normalized.name,
                version=normalized.version,
                prompt_body=normalized.prompt_body,
                purpose=normalized.purpose,
                owner=normalized.owner,
                input_schema=normalized.input_schema,
                output_schema=normalized.output_schema,
                changelog=normalized.changelog,
                test_cases=normalized.test_cases,
                status="draft",
            )
            row = PromptVersion(
                id=uuid4(),
                name=draft.name,
                version=draft.version,
                prompt_hash=_hash_prompt(draft.prompt_body),
                prompt_body=draft.prompt_body,
                metadata_json=_prompt_metadata(draft),
                status="draft",
                created_by=actor_user_id,
                approved_by=None,
            )
            self.uow.prompts.create_prompt(row)
            self._audit(
                action="prompts.create",
                actor_user_id=actor_user_id,
                resource_id=row.id,
                trace_id=trace_id,
                after_summary={
                    "name": row.name,
                    "version": row.version,
                    "status": row.status,
                    "owner": normalized.owner,
                },
            )
            self.uow.commit()
            return _prompt_public(row)

    def list_prompts(self, *, name: str | None = None) -> list[PromptDefinition]:
        with self.uow:
            rows = list(self.uow.prompts.get_prompts())
            self.uow.commit()
        prompts = [_prompt_public(row) for row in rows]
        if name is None:
            return prompts
        normalized_name = name.strip()
        return [prompt for prompt in prompts if prompt.name == normalized_name]

    def get_prompt(self, *, prompt_id: UUID) -> PromptDefinition:
        with self.uow:
            row = self.uow.prompts.get_prompt_by_id(prompt_id)
            if row is None:
                raise PromptRegistryError("PROMPT_NOT_FOUND", "Prompt version not found.", status_code=404)
            self.uow.commit()
            return _prompt_public(row)

    def approve_prompt(
        self,
        *,
        prompt_id: UUID,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> PromptStatusChange:
        with self.uow:
            row = self.uow.prompts.get_prompt_by_id(prompt_id)
            if row is None:
                raise PromptRegistryError("PROMPT_NOT_FOUND", "Prompt version not found.", status_code=404)
            if row.status == "approved":
                public = _prompt_public(row)
                self.uow.commit()
                return PromptStatusChange(
                    prompt=public,
                    active_prompt=public,
                    changed=False,
                    trace={"registry_version": PROMPT_REGISTRY_VERSION, "status": "approved"},
                )
            if row.status not in {"draft", "deprecated"}:
                raise PromptRegistryError(
                    "PROMPT_APPROVAL_FORBIDDEN",
                    "Only draft or deprecated prompts can be approved.",
                    status_code=409,
                )
            previous_active = self._active_prompt(row.name)
            row.status = "approved"
            row.approved_by = actor_user_id
            self.uow.prompts.update_prompt(row)
            self._deprecate_other_approved(row.name, keep_id=row.id)
            self._audit(
                action="prompts.approve",
                actor_user_id=actor_user_id,
                resource_id=row.id,
                trace_id=trace_id,
                before_summary={
                    "active_version": previous_active.version if previous_active else None,
                    "active_status": previous_active.status if previous_active else None,
                },
                after_summary={"name": row.name, "version": row.version, "status": row.status},
            )
            self.uow.commit()
            public = _prompt_public(row)
            return PromptStatusChange(
                prompt=public,
                active_prompt=public,
                changed=True,
                trace={
                    "registry_version": PROMPT_REGISTRY_VERSION,
                    "active_version": public.version,
                },
            )

    def rollback_prompt(
        self,
        *,
        prompt_name: str,
        target_version: str,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> PromptStatusChange:
        normalized_name = _require_text(prompt_name, code="PROMPT_NAME_REQUIRED", field_name="name")
        normalized_version = _require_text(
            target_version,
            code="PROMPT_VERSION_REQUIRED",
            field_name="version",
        )
        with self.uow:
            row = self.uow.prompts.get_prompt_by_name_version(normalized_name, normalized_version)
            if row is None:
                raise PromptRegistryError("PROMPT_NOT_FOUND", "Prompt version not found.", status_code=404)
            if row.status not in PROMPT_ROLLBACK_ALLOWED:
                raise PromptRegistryError(
                    "PROMPT_ROLLBACK_TARGET_INVALID",
                    "Rollback target must be approved or deprecated.",
                    status_code=409,
                )
            previous_active = self._active_prompt(normalized_name)
            row.status = "approved"
            row.approved_by = actor_user_id
            self.uow.prompts.update_prompt(row)
            self._deprecate_other_approved(normalized_name, keep_id=row.id)
            self._audit(
                action="prompts.rollback",
                actor_user_id=actor_user_id,
                resource_id=row.id,
                trace_id=trace_id,
                before_summary={
                    "active_version": previous_active.version if previous_active else None,
                    "active_status": previous_active.status if previous_active else None,
                },
                after_summary={"name": row.name, "version": row.version, "status": row.status},
            )
            self.uow.commit()
            public = _prompt_public(row)
            return PromptStatusChange(
                prompt=public,
                active_prompt=public,
                changed=previous_active is None or previous_active.id != public.id,
                trace={
                    "registry_version": PROMPT_REGISTRY_VERSION,
                    "rollback_to": public.version,
                },
            )

    def compare_versions(
        self,
        *,
        prompt_name: str,
        from_version: str,
        to_version: str,
    ) -> PromptComparison:
        normalized_name = _require_text(prompt_name, code="PROMPT_NAME_REQUIRED", field_name="name")
        normalized_from = _require_text(
            from_version,
            code="PROMPT_COMPARE_INPUT_INVALID",
            field_name="from_version",
        )
        normalized_to = _require_text(
            to_version,
            code="PROMPT_COMPARE_INPUT_INVALID",
            field_name="to_version",
        )
        with self.uow:
            left = self.uow.prompts.get_prompt_by_name_version(normalized_name, normalized_from)
            right = self.uow.prompts.get_prompt_by_name_version(normalized_name, normalized_to)
            if left is None or right is None:
                raise PromptRegistryError("PROMPT_NOT_FOUND", "Prompt version not found.", status_code=404)
            self.uow.commit()
        left_prompt = _prompt_public(left)
        right_prompt = _prompt_public(right)
        left_case_names = {case.name for case in left_prompt.test_cases}
        return PromptComparison(
            prompt_name=normalized_name,
            from_version=left_prompt.version,
            to_version=right_prompt.version,
            from_status=left_prompt.status,
            to_status=right_prompt.status,
            from_hash=left_prompt.prompt_hash,
            to_hash=right_prompt.prompt_hash,
            body_changed=left_prompt.prompt_hash != right_prompt.prompt_hash,
            purpose_changed=left_prompt.purpose != right_prompt.purpose,
            owner_changed=left_prompt.owner != right_prompt.owner,
            input_schema_changed=left_prompt.input_schema != right_prompt.input_schema,
            output_schema_changed=left_prompt.output_schema != right_prompt.output_schema,
            changelog_added=tuple(item for item in right_prompt.changelog if item not in left_prompt.changelog),
            test_case_names_added=tuple(
                case.name for case in right_prompt.test_cases if case.name not in left_case_names
            ),
            trace={"registry_version": PROMPT_REGISTRY_VERSION},
        )

    def resolve_active_prompt(self, *, prompt_name: str) -> PromptDefinition:
        normalized_name = _require_text(prompt_name, code="PROMPT_NAME_REQUIRED", field_name="name")
        with self.uow:
            row = self._active_prompt(normalized_name)
            if row is None:
                raise PromptRegistryError(
                    "PROMPT_ACTIVE_NOT_FOUND",
                    "No approved prompt version found.",
                    status_code=404,
                )
            self.uow.commit()
            return _prompt_public(row)

    def resolve_answer_dependencies(
        self,
        *,
        prompt_name: str,
        policy_name: str,
        model_type: str = "llm",
    ) -> tuple[PromptDefinition, UUID, UUID]:
        with self.uow:
            prompt = self._active_prompt(prompt_name)
            if prompt is None:
                raise PromptRegistryError(
                    "PROMPT_APPROVED_VERSION_REQUIRED",
                    "Answer generation requires an approved prompt version.",
                    status_code=409,
                )
            policy = self.uow.prompts.get_policy_by_name_version(policy_name, DEFAULT_POLICY_VERSION)
            if policy is None or policy.status != "approved":
                raise PromptRegistryError(
                    "POLICY_NOT_FOUND",
                    "Answer generation requires an approved policy version.",
                    status_code=409,
                )
            model = self.uow.prompts.get_default_model_configuration(model_type)
            if model is None:
                raise PromptRegistryError(
                    "PROMPT_MODEL_CONFIGURATION_REQUIRED",
                    "A default model configuration is required.",
                    status_code=409,
                )
            self.uow.commit()
            return _prompt_public(prompt), policy.id, model.id

    def create_policy(
        self,
        *,
        policy_name: str,
        version: str,
        policy_json: dict[str, Any],
        actor_user_id: UUID,
        status: str = "approved",
    ) -> PolicyVersion:
        normalized_name = _require_text(policy_name, code="PROMPT_NAME_REQUIRED", field_name="policy_name")
        normalized_version = _require_text(version, code="PROMPT_VERSION_REQUIRED", field_name="version")
        with self.uow:
            existing = self.uow.prompts.get_policy_by_name_version(normalized_name, normalized_version)
            if existing is not None:
                self.uow.commit()
                return existing
            row = PolicyVersion(
                id=uuid4(),
                policy_name=normalized_name,
                version=normalized_version,
                policy_hash=hashlib.sha256(repr(policy_json).encode("utf-8")).hexdigest(),
                policy_json=policy_json,
                status=status,
                created_by=actor_user_id,
                approved_by=actor_user_id if status == "approved" else None,
            )
            self.uow.prompts.create_policy(row)
            self.uow.commit()
            return row

    def get_policy(self, *, policy_id: UUID) -> PolicyVersion:
        with self.uow:
            row = self.uow.prompts.get_policy_by_id(policy_id)
            if row is None:
                raise PromptRegistryError("POLICY_NOT_FOUND", "Policy version not found.", status_code=404)
            self.uow.commit()
            return row

    def _deprecate_other_approved(self, prompt_name: str, *, keep_id: UUID) -> None:
        session = self._session()
        rows = session.execute(
            select(PromptVersion)
            .where(PromptVersion.name == prompt_name)
            .where(PromptVersion.status == "approved")
            .where(PromptVersion.id != keep_id)
        ).scalars().all()
        for row in rows:
            row.status = "deprecated"
            self.uow.prompts.update_prompt(row)

    def _active_prompt(self, prompt_name: str) -> PromptVersion | None:
        session = self._session()
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.name == prompt_name)
            .where(PromptVersion.status == "approved")
            .order_by(PromptVersion.updated_at.desc(), PromptVersion.created_at.desc())
        )
        row = session.execute(stmt).scalars().first()
        return row if isinstance(row, PromptVersion) or row is None else None

    def _audit(
        self,
        *,
        action: str,
        actor_user_id: UUID,
        resource_id: UUID,
        trace_id: str | None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="prompt_version",
                resource_id=resource_id,
                outcome="success",
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context={"registry_version": PROMPT_REGISTRY_VERSION},
            )
        )

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def default_answer_safety_policy() -> dict[str, Any]:
    return {
        "policy_name": "answer-safety",
        "policy_version": "risk-policy-v1",
        "status": "approved",
    }


def bootstrap_registry_defaults(
    registry: PromptRegistryService,
    *,
    actor_user_id: UUID | None = None,
) -> None:
    """Seed approved prompt, policy, and default LLM model records when missing."""
    actor_id = actor_user_id or _resolve_bootstrap_actor(registry)
    registry.create_policy(
        policy_name="answer-safety",
        version=DEFAULT_POLICY_VERSION,
        policy_json=default_answer_safety_policy(),
        actor_user_id=actor_id,
        status="approved",
    )
    default_prompt = default_answer_generation_prompt()
    with registry.uow:
        existing_prompt = registry.uow.prompts.get_prompt_by_name_version(
            default_prompt.name,
            default_prompt.version,
        )
        registry.uow.commit()
    if existing_prompt is None:
        created = registry.create_prompt(
            data=default_prompt,
            actor_user_id=actor_id,
        )
        registry.approve_prompt(prompt_id=created.id, actor_user_id=actor_id)
    elif existing_prompt.status != "approved":
        registry.approve_prompt(prompt_id=existing_prompt.id, actor_user_id=actor_id)
    _ensure_default_llm_model_configuration(registry, actor_user_id=actor_id)


def default_answer_generation_prompt() -> PromptCreate:
    return PromptCreate(
        name=DEFAULT_ANSWER_PROMPT_NAME,
        version=DEFAULT_ANSWER_PROMPT_VERSION,
        prompt_body=(
            "Create a concise Thai Islamic knowledge answer using only the provided "
            "evidence handles. Do not issue a fatwa."
        ),
        purpose="Primary answer generation prompt for verified Thai Islamic answers.",
        owner="orchestrator",
        input_schema={
            "question": "string",
            "risk_level": "string",
            "evidence_summary": "string",
        },
        output_schema={
            "summary": "string",
            "answer_th": "string",
            "citations": "array",
        },
        changelog=("Initial managed answer-generation prompt.",),
        test_cases=(
            PromptTestCase(
                name="thai-basic-answer",
                input_payload={"question": "ละหมาดคืออะไร", "risk_level": "low"},
                expected_assertions=("returns Thai answer", "does not claim fatwa"),
            ),
        ),
    )


def prompt_body_only(prompt_body: str) -> str:
    return prompt_body


def _normalize_prompt_create(data: PromptCreate) -> PromptCreate:
    name = _require_text(data.name, code="PROMPT_NAME_REQUIRED", field_name="name")
    version = _require_text(data.version, code="PROMPT_VERSION_REQUIRED", field_name="version")
    prompt_body = _require_text(
        data.prompt_body,
        code="PROMPT_BODY_REQUIRED",
        field_name="prompt_body",
    )
    owner = _require_text(data.owner, code="PROMPT_OWNER_REQUIRED", field_name="owner")
    purpose = _require_text(data.purpose, code="PROMPT_BODY_REQUIRED", field_name="purpose")
    if not data.input_schema or not data.output_schema:
        raise PromptRegistryError(
            "PROMPT_SCHEMA_REQUIRED",
            "input_schema and output_schema are required.",
            status_code=400,
        )
    status = data.status.strip().lower()
    if status not in PROMPT_STATUSES:
        raise PromptRegistryError("PROMPT_STATUS_INVALID", "Invalid prompt status.", status_code=400)
    return PromptCreate(
        name=name,
        version=version,
        prompt_body=prompt_body,
        purpose=purpose,
        owner=owner,
        input_schema=data.input_schema,
        output_schema=data.output_schema,
        changelog=tuple(item.strip() for item in data.changelog if item.strip()),
        test_cases=tuple(data.test_cases),
        status=status,
    )


def _prompt_metadata(data: PromptCreate) -> dict[str, Any]:
    return {
        "owner": data.owner,
        "purpose": data.purpose,
        "input_schema": data.input_schema,
        "output_schema": data.output_schema,
        "changelog": list(data.changelog),
        "test_cases": [case.to_json() for case in data.test_cases],
        "registry_version": PROMPT_REGISTRY_VERSION,
    }


def _prompt_public(row: PromptVersion) -> PromptDefinition:
    metadata = dict(row.metadata_json or {})
    cases = tuple(
        PromptTestCase(
            name=str(item["name"]),
            input_payload=dict(item["input_payload"]),
            expected_assertions=tuple(str(value) for value in item["expected_assertions"]),
        )
        for item in metadata.get("test_cases", [])
    )
    return PromptDefinition(
        id=row.id,
        name=row.name,
        version=row.version,
        prompt_body=row.prompt_body,
        status=row.status,
        owner=str(metadata.get("owner", "")),
        purpose=str(metadata.get("purpose", "")),
        input_schema=dict(metadata.get("input_schema", {})),
        output_schema=dict(metadata.get("output_schema", {})),
        changelog=tuple(str(item) for item in metadata.get("changelog", [])),
        test_cases=cases,
        prompt_hash=row.prompt_hash,
        created_by=row.created_by,
        approved_by=row.approved_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        active=row.status == "approved",
    )


def _hash_prompt(prompt_body: str) -> str:
    return hashlib.sha256(prompt_body.encode("utf-8")).hexdigest()


def _require_text(value: str, *, code: PromptRegistryErrorCode, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PromptRegistryError(code, f"{field_name} is required.", status_code=400)
    return normalized


def _resolve_bootstrap_actor(registry: PromptRegistryService) -> UUID:
    with registry.uow:
        session = registry._session()
        user = session.execute(select(User).limit(1)).scalar_one_or_none()
        if user is None:
            raise PromptRegistryError(
                "PROMPT_OWNER_REQUIRED",
                "A bootstrap actor user is required before seeding prompt defaults.",
                status_code=409,
            )
        actor_id = user.id
        registry.uow.commit()
        return actor_id


def _ensure_default_llm_model_configuration(
    registry: PromptRegistryService,
    *,
    actor_user_id: UUID,
) -> None:
    with registry.uow:
        session = registry._session()
        existing = registry.uow.prompts.get_default_model_configuration("llm")
        if existing is not None:
            registry.uow.commit()
            return
        provider = session.execute(
            select(Provider).where(Provider.name == "Local LLM").limit(1)
        ).scalar_one_or_none()
        if provider is None:
            provider = Provider(
                id=uuid4(),
                name="Local LLM",
                provider_type="llm",
                status="enabled",
                data_policy_json={"classification": "internal"},
                created_by=actor_user_id,
            )
            session.add(provider)
            session.flush()
        session.add(
            ModelConfiguration(
                id=uuid4(),
                provider_id=provider.id,
                model_name="mock-llm",
                model_type="llm",
                configuration_json={"temperature": 0.0, "max_output_tokens": 512},
                is_default=True,
                status="enabled",
                created_by=actor_user_id,
            )
        )
        registry.uow.commit()
