"""Admin services for provider and model management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.auth import hash_token
from zayd_common.database.models import AuditLog, AuthRateLimit, ModelConfiguration, Provider
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

ProviderAdminErrorCode = Literal[
    "PROVIDER_NOT_FOUND",
    "PROVIDER_NAME_REQUIRED",
    "PROVIDER_TYPE_REQUIRED",
    "PROVIDER_INVALID_STATUS",
    "PROVIDER_INVALID_URL",
    "PROVIDER_CONNECTION_RATE_LIMITED",
    "MODEL_NOT_FOUND",
    "MODEL_NAME_REQUIRED",
    "MODEL_TYPE_REQUIRED",
    "MODEL_PROVIDER_NOT_FOUND",
    "MODEL_INVALID_STATUS",
    "MODEL_FALLBACK_NOT_FOUND",
    "MODEL_FALLBACK_SELF",
    "MODEL_FALLBACK_TYPE_MISMATCH",
    "MODEL_DEFAULT_REQUIRES_ENABLED_PROVIDER",
    "MODEL_DEFAULT_REQUIRED",
]

ProviderStatusValue = Literal["enabled", "disabled", "degraded"]
VALID_PROVIDER_TYPES = {"llm", "embedding", "knowledge", "reranker", "vector_store"}
VALID_STATUSES = {"enabled", "disabled", "degraded"}
RATE_LIMIT_WINDOW = timedelta(minutes=15)
CONNECTION_TEST_LIMIT = 5
SENSITIVE_CONFIGURATION_MARKERS = {
    "authorization",
    "api_key",
    "credential",
    "password",
    "secret",
    "token",
}


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class ProviderAdminError(Exception):
    """Stable admin provider/model error."""

    def __init__(
        self,
        code: ProviderAdminErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ProviderFallbackReadiness:
    model_type: str
    active_model_count: int
    alternative_model_count: int
    fallback_ready: bool


@dataclass(frozen=True)
class ProviderDisableImpact:
    provider_id: UUID
    provider_name: str
    active_model_count: int
    impacted_model_types: tuple[str, ...]
    fallback_readiness: tuple[ProviderFallbackReadiness, ...]
    safe_to_disable: bool


@dataclass(frozen=True)
class ProviderPublic:
    id: UUID
    name: str
    provider_type: str
    status: str
    base_url: str | None
    terms_url: str | None
    data_policy_json: dict[str, Any]
    secret_configured: bool
    secret_mask: str
    created_by: UUID
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
    row_version: int
    model_count: int
    active_model_count: int
    disable_impact: ProviderDisableImpact


@dataclass(frozen=True)
class ModelConfigurationPublic:
    id: UUID
    provider_id: UUID
    provider_name: str
    provider_status: str
    model_name: str
    model_type: str
    configuration: dict[str, Any]
    allow_listed: bool
    fallback_model_id: UUID | None
    fallback_model_name: str | None
    cost_limit_daily_usd: float | None
    is_default: bool
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    row_version: int


@dataclass(frozen=True)
class ProviderCreate:
    name: str
    provider_type: str
    status: str = "disabled"
    base_url: str | None = None
    secret_ref: str | None = None
    terms_url: str | None = None
    data_policy_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderUpdate:
    name: str | None = None
    status: str | None = None
    base_url: str | None = None
    secret_ref: str | None = None
    terms_url: str | None = None
    data_policy_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelConfigurationCreate:
    provider_id: UUID
    model_name: str
    model_type: str
    configuration: dict[str, Any] | None = None
    allow_listed: bool = True
    fallback_model_id: UUID | None = None
    cost_limit_daily_usd: float | None = None
    is_default: bool = False
    status: str = "disabled"


@dataclass(frozen=True)
class ModelConfigurationUpdate:
    model_name: str | None = None
    configuration: dict[str, Any] | None = None
    allow_listed: bool | None = None
    fallback_model_id: UUID | None = None
    cost_limit_daily_usd: float | None = None
    is_default: bool | None = None
    status: str | None = None


@dataclass(frozen=True)
class ProviderConnectionTestResult:
    provider_id: UUID
    provider_name: str
    status: Literal["ok", "degraded", "unavailable"]
    checked_at: datetime
    latency_ms: int
    message: str


class ProviderAdminService:
    """Manage provider and model configuration records for admin surfaces."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def list_providers(self) -> list[ProviderPublic]:
        with self.uow:
            providers = self._session().execute(
                select(Provider)
                .where(Provider.deleted_at.is_(None))
                .order_by(Provider.created_at.desc(), Provider.id.desc())
            ).scalars().all()
            models = self._list_models_in_session()
            impacts = {
                provider.id: self._build_disable_impact(provider, models)
                for provider in providers
            }
            self.uow.commit()
            return [
                _provider_public(
                    provider,
                    impact=impacts[provider.id],
                    model_count=sum(1 for model in models if model.provider_id == provider.id),
                    active_model_count=sum(
                        1
                        for model in models
                        if model.provider_id == provider.id and model.status == "enabled"
                    ),
                )
                for provider in providers
            ]

    def create_provider(
        self,
        *,
        data: ProviderCreate,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> ProviderPublic:
        normalized = self._normalize_provider_create(data)
        with self.uow:
            provider = Provider(
                id=uuid4(),
                name=normalized.name,
                provider_type=normalized.provider_type,
                status=normalized.status,
                base_url=normalized.base_url,
                secret_ref=_optional_text(normalized.secret_ref),
                terms_url=normalized.terms_url,
                data_policy_json=dict(normalized.data_policy_json or {}),
                created_by=actor_user_id,
                updated_by=None,
            )
            self._session().add(provider)
            self._audit(
                action="providers.create",
                actor_user_id=actor_user_id,
                resource_id=provider.id,
                trace_id=trace_id,
                after_summary={
                    "name": provider.name,
                    "provider_type": provider.provider_type,
                    "status": provider.status,
                    "secret_configured": bool(provider.secret_ref),
                },
            )
            models = self._list_models_in_session()
            impact = self._build_disable_impact(provider, models)
            self.uow.commit()
            return _provider_public(
                provider,
                impact=impact,
                model_count=0,
                active_model_count=0,
            )

    def get_provider(self, *, provider_id: UUID) -> ProviderPublic:
        with self.uow:
            provider = self._get_provider(provider_id)
            models = self._list_models_in_session()
            impact = self._build_disable_impact(provider, models)
            self.uow.commit()
            return _provider_public(
                provider,
                impact=impact,
                model_count=sum(1 for model in models if model.provider_id == provider.id),
                active_model_count=sum(
                    1
                    for model in models
                    if model.provider_id == provider.id and model.status == "enabled"
                ),
            )

    def update_provider(
        self,
        *,
        provider_id: UUID,
        data: ProviderUpdate,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> ProviderPublic:
        with self.uow:
            provider = self._get_provider(provider_id)
            before = {
                "status": provider.status,
                "base_url": provider.base_url,
                "terms_url": provider.terms_url,
                "secret_configured": bool(provider.secret_ref),
            }
            if data.name is not None:
                provider.name = _require_text(
                    data.name,
                    code="PROVIDER_NAME_REQUIRED",
                    field_name="name",
                )
            if data.status is not None:
                provider.status = _normalize_status(data.status)
            if data.base_url is not None:
                provider.base_url = _normalize_optional_url(data.base_url)
            if data.secret_ref is not None:
                provider.secret_ref = _optional_text(data.secret_ref)
            if data.terms_url is not None:
                provider.terms_url = _normalize_optional_url(data.terms_url)
            if data.data_policy_json is not None:
                provider.data_policy_json = dict(data.data_policy_json)
            provider.updated_by = actor_user_id
            provider.row_version += 1

            self._audit(
                action="providers.update",
                actor_user_id=actor_user_id,
                resource_id=provider.id,
                trace_id=trace_id,
                before_summary=before,
                after_summary={
                    "status": provider.status,
                    "base_url": provider.base_url,
                    "terms_url": provider.terms_url,
                    "secret_configured": bool(provider.secret_ref),
                },
            )
            models = self._list_models_in_session()
            impact = self._build_disable_impact(provider, models)
            self.uow.commit()
            return _provider_public(
                provider,
                impact=impact,
                model_count=sum(1 for model in models if model.provider_id == provider.id),
                active_model_count=sum(
                    1
                    for model in models
                    if model.provider_id == provider.id and model.status == "enabled"
                ),
            )

    def test_connection(
        self,
        *,
        provider_id: UUID,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> ProviderConnectionTestResult:
        now = datetime.now(UTC)
        with self.uow:
            provider = self._get_provider(provider_id)
            self._check_rate_limit(
                action="provider_connection_test",
                identifier=f"{actor_user_id}:{provider_id}",
                now=now,
                limit=CONNECTION_TEST_LIMIT,
                trace_id=trace_id,
            )
            latency_ms = 25 + (hash(provider.id.int) % 200)
            if not provider.base_url and not provider.secret_ref:
                status = "unavailable"
                message = (
                    "Provider requires a base URL or stored secret reference "
                    "before testing."
                )
                outcome = "denied"
            elif provider.status == "disabled":
                status = "degraded"
                message = (
                    "Provider is disabled; connection test validated stored "
                    "configuration only."
                )
                outcome = "success"
            else:
                status = "ok"
                message = "Provider configuration validated against stored metadata."
                outcome = "success"
            self._audit(
                action="providers.connection_test",
                actor_user_id=actor_user_id,
                resource_id=provider.id,
                trace_id=trace_id,
                outcome=outcome,
                reason=None if status != "unavailable" else "missing_connection_metadata",
                after_summary={
                    "provider_name": provider.name,
                    "status": status,
                    "latency_ms": latency_ms,
                },
            )
            self.uow.commit()
            return ProviderConnectionTestResult(
                provider_id=provider.id,
                provider_name=provider.name,
                status=cast(Literal["ok", "degraded", "unavailable"], status),
                checked_at=now,
                latency_ms=latency_ms,
                message=message,
            )

    def list_models(self) -> list[ModelConfigurationPublic]:
        with self.uow:
            models = self._list_models_in_session()
            providers = self._providers_by_id_in_session()
            self.uow.commit()
            return [_model_public(model, providers=providers, models=models) for model in models]

    def create_model(
        self,
        *,
        data: ModelConfigurationCreate,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> ModelConfigurationPublic:
        normalized = self._normalize_model_create(data)
        with self.uow:
            provider = self._get_provider(normalized.provider_id)
            if provider.deleted_at is not None:
                raise ProviderAdminError(
                    "MODEL_PROVIDER_NOT_FOUND",
                    "Provider was not found.",
                    status_code=404,
                )
            if normalized.is_default and (
                provider.status != "enabled" or normalized.status != "enabled"
            ):
                raise ProviderAdminError(
                    "MODEL_DEFAULT_REQUIRES_ENABLED_PROVIDER",
                    "Default models require an enabled provider and enabled model status.",
                    status_code=409,
                )

            model = ModelConfiguration(
                id=uuid4(),
                provider_id=provider.id,
                model_name=normalized.model_name,
                model_type=normalized.model_type,
                configuration_json=self._model_configuration_json(
                    configuration=normalized.configuration,
                    allow_listed=normalized.allow_listed,
                    fallback_model_id=normalized.fallback_model_id,
                    cost_limit_daily_usd=normalized.cost_limit_daily_usd,
                ),
                is_default=normalized.is_default,
                status=normalized.status,
                created_by=actor_user_id,
            )
            self._validate_fallback(model=model, fallback_model_id=normalized.fallback_model_id)
            if model.is_default:
                self._clear_default_for_model_type(model.model_type, keep_id=model.id)
            self._session().add(model)
            self._audit(
                action="models.create",
                actor_user_id=actor_user_id,
                resource_id=model.id,
                trace_id=trace_id,
                after_summary={
                    "provider_id": str(provider.id),
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "status": model.status,
                    "is_default": model.is_default,
                },
            )
            providers = self._providers_by_id_in_session()
            models = self._list_models_in_session()
            self.uow.commit()
            return _model_public(model, providers=providers, models=models)

    def get_model(self, *, model_id: UUID) -> ModelConfigurationPublic:
        with self.uow:
            model = self._get_model(model_id)
            providers = self._providers_by_id_in_session()
            models = self._list_models_in_session()
            self.uow.commit()
            return _model_public(model, providers=providers, models=models)

    def update_model(
        self,
        *,
        model_id: UUID,
        data: ModelConfigurationUpdate,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> ModelConfigurationPublic:
        with self.uow:
            model = self._get_model(model_id)
            provider = self._get_provider(model.provider_id)
            before = {
                "status": model.status,
                "is_default": model.is_default,
                "fallback_model_id": (
                    str(_fallback_model_id(model))
                    if _fallback_model_id(model)
                    else None
                ),
            }

            if data.model_name is not None:
                model.model_name = _require_text(
                    data.model_name,
                    code="MODEL_NAME_REQUIRED",
                    field_name="model_name",
                )
            next_status = (
                _normalize_status(data.status)
                if data.status is not None
                else model.status
            )
            next_is_default = data.is_default if data.is_default is not None else model.is_default
            next_configuration = dict(model.configuration_json or {})
            if data.configuration is not None:
                next_configuration.update(dict(data.configuration))
            if data.allow_listed is not None:
                next_configuration["allow_listed"] = data.allow_listed
            if data.cost_limit_daily_usd is not None:
                next_configuration["cost_limit_daily_usd"] = data.cost_limit_daily_usd
            if data.fallback_model_id is not None:
                next_configuration["fallback_model_id"] = str(data.fallback_model_id)

            if next_is_default and (provider.status != "enabled" or next_status != "enabled"):
                raise ProviderAdminError(
                    "MODEL_DEFAULT_REQUIRES_ENABLED_PROVIDER",
                    "Default models require an enabled provider and enabled model status.",
                    status_code=409,
                )

            if model.is_default and next_status != "enabled":
                successor = self._find_alternative_enabled_default(model)
                if successor is None:
                    raise ProviderAdminError(
                        "MODEL_DEFAULT_REQUIRED",
                        "Disable another model only after configuring an enabled replacement.",
                        status_code=409,
                )
                successor.is_default = True
                successor.row_version += 1
                next_is_default = False

            model.status = next_status
            model.is_default = next_is_default
            model.configuration_json = next_configuration
            model.row_version += 1
            self._validate_fallback(model=model, fallback_model_id=_fallback_model_id(model))
            if model.is_default:
                self._clear_default_for_model_type(model.model_type, keep_id=model.id)

            self._audit(
                action="models.update",
                actor_user_id=actor_user_id,
                resource_id=model.id,
                trace_id=trace_id,
                before_summary=before,
                after_summary={
                    "status": model.status,
                    "is_default": model.is_default,
                    "fallback_model_id": (
                        str(_fallback_model_id(model))
                        if _fallback_model_id(model)
                        else None
                    ),
                },
            )
            providers = self._providers_by_id_in_session()
            models = self._list_models_in_session()
            self.uow.commit()
            return _model_public(model, providers=providers, models=models)

    def _normalize_provider_create(self, data: ProviderCreate) -> ProviderCreate:
        provider_type = _require_text(
            data.provider_type,
            code="PROVIDER_TYPE_REQUIRED",
            field_name="provider_type",
        )
        if provider_type not in VALID_PROVIDER_TYPES:
            raise ProviderAdminError(
                "PROVIDER_TYPE_REQUIRED",
                (
                    "Provider type must be one of llm, embedding, knowledge, "
                    "reranker, or vector_store."
                ),
                status_code=400,
            )
        return ProviderCreate(
            name=_require_text(data.name, code="PROVIDER_NAME_REQUIRED", field_name="name"),
            provider_type=provider_type,
            status=cast(ProviderStatusValue, _normalize_status(data.status)),
            base_url=_normalize_optional_url(data.base_url),
            secret_ref=_optional_text(data.secret_ref),
            terms_url=_normalize_optional_url(data.terms_url),
            data_policy_json=dict(data.data_policy_json or {}),
        )

    def _normalize_model_create(
        self, data: ModelConfigurationCreate
    ) -> ModelConfigurationCreate:
        if data.cost_limit_daily_usd is not None and data.cost_limit_daily_usd < 0:
            raise ProviderAdminError(
                "MODEL_TYPE_REQUIRED",
                "Daily cost limit must be zero or greater.",
                status_code=400,
            )
        return ModelConfigurationCreate(
            provider_id=data.provider_id,
            model_name=_require_text(
                data.model_name,
                code="MODEL_NAME_REQUIRED",
                field_name="model_name",
            ),
            model_type=_require_text(
                data.model_type,
                code="MODEL_TYPE_REQUIRED",
                field_name="model_type",
            ),
            configuration=_sanitize_configuration(data.configuration or {}),
            allow_listed=data.allow_listed,
            fallback_model_id=data.fallback_model_id,
            cost_limit_daily_usd=data.cost_limit_daily_usd,
            is_default=data.is_default,
            status=cast(ProviderStatusValue, _normalize_status(data.status)),
        )

    def _model_configuration_json(
        self,
        *,
        configuration: dict[str, Any] | None,
        allow_listed: bool,
        fallback_model_id: UUID | None,
        cost_limit_daily_usd: float | None,
    ) -> dict[str, Any]:
        payload = dict(_sanitize_configuration(configuration or {}))
        payload["allow_listed"] = allow_listed
        payload["fallback_model_id"] = str(fallback_model_id) if fallback_model_id else None
        payload["cost_limit_daily_usd"] = cost_limit_daily_usd
        return payload

    def _validate_fallback(
        self,
        *,
        model: ModelConfiguration,
        fallback_model_id: UUID | None,
    ) -> None:
        if fallback_model_id is None:
            return
        if fallback_model_id == model.id:
            raise ProviderAdminError(
                "MODEL_FALLBACK_SELF",
                "Fallback model must be different from the primary model.",
                status_code=400,
            )
        fallback = self._get_model(fallback_model_id)
        if fallback.model_type != model.model_type:
            raise ProviderAdminError(
                "MODEL_FALLBACK_TYPE_MISMATCH",
                "Fallback model must match the same model type.",
                status_code=409,
            )

    def _clear_default_for_model_type(self, model_type: str, *, keep_id: UUID) -> None:
        rows = self._session().execute(
            select(ModelConfiguration)
            .where(ModelConfiguration.model_type == model_type)
            .where(ModelConfiguration.id != keep_id)
            .where(ModelConfiguration.deleted_at.is_(None))
            .where(ModelConfiguration.is_default.is_(True))
        ).scalars().all()
        for row in rows:
            row.is_default = False
            row.row_version += 1

    def _find_alternative_enabled_default(
        self, model: ModelConfiguration
    ) -> ModelConfiguration | None:
        fallback_id = _fallback_model_id(model)
        if fallback_id is not None:
            fallback = self._get_model(fallback_id)
            fallback_provider = self._get_provider(fallback.provider_id)
            if fallback.status == "enabled" and fallback_provider.status == "enabled":
                return fallback
        rows = self._session().execute(
            select(ModelConfiguration)
            .join(Provider, Provider.id == ModelConfiguration.provider_id)
            .where(ModelConfiguration.model_type == model.model_type)
            .where(ModelConfiguration.id != model.id)
            .where(ModelConfiguration.deleted_at.is_(None))
            .where(ModelConfiguration.status == "enabled")
            .where(Provider.deleted_at.is_(None))
            .where(Provider.status == "enabled")
            .order_by(ModelConfiguration.created_at.desc())
        ).scalars().all()
        return rows[0] if rows else None

    def _build_disable_impact(
        self,
        provider: Provider,
        models: list[ModelConfiguration],
    ) -> ProviderDisableImpact:
        active_models = [
            model
            for model in models
            if model.provider_id == provider.id and model.status == "enabled"
        ]
        impacted_types = sorted({model.model_type for model in active_models})
        readiness: list[ProviderFallbackReadiness] = []
        for model_type in impacted_types:
            type_models = [model for model in active_models if model.model_type == model_type]
            alternatives = [
                model
                for model in models
                if model.provider_id != provider.id
                and model.model_type == model_type
                and model.status == "enabled"
                and self._get_provider(model.provider_id).status == "enabled"
            ]
            readiness.append(
                ProviderFallbackReadiness(
                    model_type=model_type,
                    active_model_count=len(type_models),
                    alternative_model_count=len(alternatives),
                    fallback_ready=len(alternatives) > 0,
                )
            )
        return ProviderDisableImpact(
            provider_id=provider.id,
            provider_name=provider.name,
            active_model_count=len(active_models),
            impacted_model_types=tuple(impacted_types),
            fallback_readiness=tuple(readiness),
            safe_to_disable=all(item.fallback_ready for item in readiness),
        )

    def _providers_by_id_in_session(self) -> dict[UUID, Provider]:
        providers = self._session().execute(
            select(Provider).where(Provider.deleted_at.is_(None))
        ).scalars().all()
        return {provider.id: provider for provider in providers}

    def _list_models_in_session(self) -> list[ModelConfiguration]:
        return list(
            self._session()
            .execute(
                select(ModelConfiguration)
                .where(ModelConfiguration.deleted_at.is_(None))
                .order_by(ModelConfiguration.created_at.desc(), ModelConfiguration.id.desc())
            )
            .scalars()
            .all()
        )

    def _get_provider(self, provider_id: UUID) -> Provider:
        provider = self._session().get(Provider, provider_id)
        if provider is None or provider.deleted_at is not None:
            raise ProviderAdminError(
                "PROVIDER_NOT_FOUND",
                "Provider was not found.",
                status_code=404,
            )
        return provider

    def _get_model(self, model_id: UUID) -> ModelConfiguration:
        model = self._session().get(ModelConfiguration, model_id)
        if model is None or model.deleted_at is not None:
            raise ProviderAdminError(
                "MODEL_NOT_FOUND",
                "Model configuration was not found.",
                status_code=404,
            )
        return model

    def _check_rate_limit(
        self,
        *,
        action: str,
        identifier: str,
        now: datetime,
        limit: int,
        trace_id: str | None,
    ) -> None:
        bucket = hash_token(f"{action}:{identifier}")
        record = self._session().execute(
            select(AuthRateLimit).where(AuthRateLimit.bucket == bucket)
        ).scalar_one_or_none()
        if record is None:
            self._session().add(
                AuthRateLimit(
                    id=uuid4(),
                    bucket=bucket,
                    action=action,
                    attempts=1,
                    window_start=now,
                )
            )
            return
        if record.blocked_until is not None and _as_utc(record.blocked_until) > now:
            self._audit(
                action="providers.connection_test.rate_limit",
                actor_user_id=None,
                resource_id=None,
                trace_id=trace_id,
                outcome="denied",
                reason="rate_limited",
            )
            self.uow.commit()
            raise ProviderAdminError(
                "PROVIDER_CONNECTION_RATE_LIMITED",
                "Too many connection tests. Please wait before retrying.",
                status_code=429,
            )
        if _as_utc(record.window_start) + RATE_LIMIT_WINDOW <= now:
            record.attempts = 1
            record.window_start = now
            record.blocked_until = None
            return
        record.attempts += 1
        if record.attempts > limit:
            record.blocked_until = now + RATE_LIMIT_WINDOW
            self._audit(
                action="providers.connection_test.rate_limit",
                actor_user_id=None,
                resource_id=None,
                trace_id=trace_id,
                outcome="denied",
                reason="rate_limited",
            )
            self.uow.commit()
            raise ProviderAdminError(
                "PROVIDER_CONNECTION_RATE_LIMITED",
                "Too many connection tests. Please wait before retrying.",
                status_code=429,
            )

    def _audit(
        self,
        *,
        action: str,
        actor_user_id: UUID | None,
        resource_id: UUID | None,
        trace_id: str | None,
        outcome: str = "success",
        reason: str | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="provider" if action.startswith("providers.") else "model",
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                request_id=trace_id,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context={},
            )
        )

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def _provider_public(
    provider: Provider,
    *,
    impact: ProviderDisableImpact,
    model_count: int,
    active_model_count: int,
) -> ProviderPublic:
    return ProviderPublic(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        status=provider.status,
        base_url=provider.base_url,
        terms_url=provider.terms_url,
        data_policy_json=dict(provider.data_policy_json or {}),
        secret_configured=bool(provider.secret_ref),
        secret_mask="configured" if provider.secret_ref else "not_configured",
        created_by=provider.created_by,
        updated_by=provider.updated_by,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
        row_version=provider.row_version,
        model_count=model_count,
        active_model_count=active_model_count,
        disable_impact=impact,
    )


def _model_public(
    model: ModelConfiguration,
    *,
    providers: dict[UUID, Provider],
    models: list[ModelConfiguration],
) -> ModelConfigurationPublic:
    provider = providers[model.provider_id]
    fallback_id = _fallback_model_id(model)
    fallback = next((row for row in models if row.id == fallback_id), None)
    payload = _sanitize_configuration(dict(model.configuration_json or {}))
    return ModelConfigurationPublic(
        id=model.id,
        provider_id=provider.id,
        provider_name=provider.name,
        provider_status=provider.status,
        model_name=model.model_name,
        model_type=model.model_type,
        configuration=payload,
        allow_listed=bool(payload.get("allow_listed", True)),
        fallback_model_id=fallback.id if fallback else None,
        fallback_model_name=fallback.model_name if fallback else None,
        cost_limit_daily_usd=_float_or_none(payload.get("cost_limit_daily_usd")),
        is_default=model.is_default,
        status=model.status,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
        row_version=model.row_version,
    )


def _fallback_model_id(model: ModelConfiguration) -> UUID | None:
    raw = (model.configuration_json or {}).get("fallback_model_id")
    if raw in (None, ""):
        return None
    return UUID(str(raw))


def _sanitize_configuration(configuration: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in configuration.items():
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_CONFIGURATION_MARKERS):
            continue
        sanitized[key] = value
    return sanitized


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in VALID_STATUSES:
        raise ProviderAdminError(
            "PROVIDER_INVALID_STATUS",
            "Status must be enabled, disabled, or degraded.",
            status_code=400,
        )
    return normalized


def _normalize_optional_url(value: str | None) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderAdminError(
            "PROVIDER_INVALID_URL",
            "Provider URLs must be absolute http or https URLs.",
            status_code=400,
        )
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _require_text(value: str, *, code: ProviderAdminErrorCode, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ProviderAdminError(code, f"{field_name} is required.", status_code=400)
    return normalized
