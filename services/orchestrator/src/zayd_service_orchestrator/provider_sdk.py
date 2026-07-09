"""Provider contracts, allow-list loading, and deterministic mock providers."""

from __future__ import annotations

import hashlib
import math
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

PROVIDER_SDK_VERSION = "provider-sdk-v1"

ProviderKind = Literal["llm", "embedding", "knowledge", "reranker", "vector_store"]
ProviderHealthStatus = Literal["ok", "degraded", "unavailable"]
ProviderErrorCode = Literal[
    "PROVIDER_CONFIG_INVALID",
    "PROVIDER_DISABLED",
    "PROVIDER_HEALTH_UNAVAILABLE",
    "PROVIDER_INPUT_INVALID",
    "PROVIDER_NOT_ALLOWED",
    "PROVIDER_RESPONSE_INVALID",
]


class ProviderSDKError(Exception):
    """Stable provider SDK error for orchestration and adapter code."""

    def __init__(self, code: ProviderErrorCode, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ProviderIdentity:
    name: str
    kind: ProviderKind
    version: str
    api_version: str = PROVIDER_SDK_VERSION
    model_id: str | None = None
    model_revision: str | None = None


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_streaming: bool = False
    supports_structured_output: bool = False
    supports_batching: bool = False
    supports_multilingual: bool = True
    supports_health_check: bool = True
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    dimensions: int | None = None
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderStoragePolicy:
    persistent_storage: bool = False
    max_cache_ttl_seconds: int = 0
    data_sharing_allowed: bool = False
    stores_user_content: bool = False


@dataclass(frozen=True)
class ProviderConfig:
    provider_name: str
    kind: ProviderKind
    enabled: bool = True
    base_url: str | None = None
    secret_ref: str | None = None
    timeout_ms: int = 10_000
    max_retries: int = 1
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderHealth:
    status: ProviderHealthStatus
    checked_at: datetime
    provider_name: str
    kind: ProviderKind
    sdk_version: str = PROVIDER_SDK_VERSION
    message: str | None = None
    latency_ms: float | None = None
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str


@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    trace_id: str | None = None
    temperature: float = 0.0
    max_output_tokens: int = 512
    response_format: Literal["text", "json"] = "text"
    safety_context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    text: str
    finish_reason: Literal["stop", "length", "tool_call", "error"]
    provider: ProviderIdentity
    usage: LLMUsage
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
    language: str
    normalize: bool = True
    trace_id: str | None = None


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    dimensions: int
    provider: ProviderIdentity
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeSearchRequest:
    query: str
    filters: dict[str, object] = field(default_factory=dict)
    limit: int = 10
    trace_id: str | None = None


@dataclass(frozen=True)
class KnowledgeSearchResult:
    provider_document_id: str
    title: str
    snippet: str
    score: float
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeSearchResponse:
    results: tuple[KnowledgeSearchResult, ...]
    provider: ProviderIdentity
    storage_policy: ProviderStoragePolicy
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeDocument:
    provider_document_id: str
    title: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RerankRequest:
    query: str
    documents: tuple[KnowledgeSearchResult, ...]
    trace_id: str | None = None


@dataclass(frozen=True)
class RerankResult:
    provider_document_id: str
    score: float
    rank: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RerankResponse:
    results: tuple[RerankResult, ...]
    provider: ProviderIdentity
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorRecord:
    record_id: str
    vector: tuple[float, ...]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchRequest:
    vector: tuple[float, ...]
    filters: dict[str, object] = field(default_factory=dict)
    limit: int = 10
    trace_id: str | None = None


@dataclass(frozen=True)
class VectorSearchResult:
    record: VectorRecord
    score: float
    rank: int


class Provider(Protocol):
    def identity(self) -> ProviderIdentity: ...

    def capabilities(self) -> ProviderCapabilities: ...

    def validate_config(self, config: ProviderConfig) -> ProviderValidationResult: ...

    async def health_check(self) -> ProviderHealth: ...


class LLMProvider(Provider, Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...


class EmbeddingProvider(Provider, Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

    def dimensions(self) -> int: ...


class KnowledgeProvider(Provider, Protocol):
    async def search(self, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse: ...

    async def fetch_document(self, provider_document_id: str) -> KnowledgeDocument: ...

    def storage_policy(self) -> ProviderStoragePolicy: ...


class RerankerProvider(Provider, Protocol):
    async def rerank(self, request: RerankRequest) -> RerankResponse: ...


class VectorStoreProvider(Provider, Protocol):
    async def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]: ...

    async def upsert(self, records: tuple[VectorRecord, ...]) -> int: ...

    async def delete(self, record_ids: tuple[str, ...]) -> int: ...


@dataclass(frozen=True)
class ProviderRegistration:
    provider: Provider
    enabled: bool = True


class AllowListedProviderRegistry:
    """Loads providers only when they are explicitly registered and enabled."""

    def __init__(self, registrations: tuple[ProviderRegistration, ...] = ()) -> None:
        self._providers: dict[tuple[ProviderKind, str], ProviderRegistration] = {}
        for registration in registrations:
            self.register(registration.provider, enabled=registration.enabled)

    def register(self, provider: Provider, *, enabled: bool = True) -> None:
        identity = provider.identity()
        self._providers[(identity.kind, identity.name)] = ProviderRegistration(
            provider=provider,
            enabled=enabled,
        )

    def allowed_provider_names(self, kind: ProviderKind | None = None) -> tuple[str, ...]:
        names = [
            provider_name
            for (provider_kind, provider_name), registration in self._providers.items()
            if registration.enabled and (kind is None or provider_kind == kind)
        ]
        return tuple(sorted(names))

    def load(self, kind: ProviderKind, provider_name: str) -> Provider:
        registration = self._providers.get((kind, provider_name))
        if registration is None:
            raise ProviderSDKError(
                "PROVIDER_NOT_ALLOWED",
                "Provider is not in the explicit allow-list.",
                status_code=403,
            )
        if not registration.enabled:
            raise ProviderSDKError(
                "PROVIDER_DISABLED",
                "Provider is registered but disabled.",
                status_code=403,
            )
        return registration.provider


class _MockBaseProvider:
    def __init__(
        self,
        *,
        name: str,
        kind: ProviderKind,
        version: str = "mock-provider-v1",
        model_id: str | None = None,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._identity = ProviderIdentity(
            name=name,
            kind=kind,
            version=version,
            model_id=model_id,
            model_revision=version,
        )
        self._capabilities = capabilities or ProviderCapabilities()

    def identity(self) -> ProviderIdentity:
        return self._identity

    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def validate_config(self, config: ProviderConfig) -> ProviderValidationResult:
        errors: list[str] = []
        if config.provider_name != self._identity.name:
            errors.append("provider_name does not match provider identity")
        if config.kind != self._identity.kind:
            errors.append("kind does not match provider identity")
        if config.timeout_ms < 1 or config.timeout_ms > 120_000:
            errors.append("timeout_ms must be between 1 and 120000")
        if config.max_retries < 0 or config.max_retries > 5:
            errors.append("max_retries must be between 0 and 5")
        if not config.enabled:
            errors.append("provider config is disabled")
        return ProviderValidationResult(valid=not errors, errors=tuple(errors))

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            status="ok",
            checked_at=datetime.now(UTC),
            provider_name=self._identity.name,
            kind=self._identity.kind,
            message="mock provider ready",
        )


class MockLLMProvider(_MockBaseProvider):
    def __init__(self, *, name: str = "mock-llm") -> None:
        super().__init__(
            name=name,
            kind="llm",
            model_id="mock-deterministic-llm",
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_structured_output=True,
                max_input_tokens=8_192,
                max_output_tokens=2_048,
                capabilities=("generate", "stream"),
            ),
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.messages:
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "At least one LLM message is required.",
            )
        user_text = "\n".join(
            message.content for message in request.messages if message.role == "user"
        )
        digest = hashlib.sha256(user_text.encode("utf-8")).hexdigest()[:12]
        text = f"mock-response:{digest}"
        if request.response_format == "json":
            text = f'{{"response":"mock-response","digest":"{digest}"}}'
        usage = LLMUsage(
            input_tokens=sum(_token_count(message.content) for message in request.messages),
            output_tokens=_token_count(text),
            total_tokens=sum(_token_count(message.content) for message in request.messages)
            + _token_count(text),
        )
        return LLMResponse(
            text=text,
            finish_reason="stop",
            provider=self.identity(),
            usage=usage,
            trace={"sdk_version": PROVIDER_SDK_VERSION, "trace_id": request.trace_id},
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        for token in response.text.split(":"):
            yield token


class MockEmbeddingProvider(_MockBaseProvider):
    def __init__(self, *, name: str = "mock-embedding", dimensions: int = 8) -> None:
        if dimensions < 1:
            raise ProviderSDKError(
                "PROVIDER_CONFIG_INVALID",
                "Embedding dimensions must be positive.",
            )
        self._dimensions = dimensions
        super().__init__(
            name=name,
            kind="embedding",
            model_id="mock-hash-embedding",
            capabilities=ProviderCapabilities(
                supports_batching=True,
                dimensions=dimensions,
                capabilities=("embed_query", "embed_documents"),
            ),
        )

    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        if not request.texts or any(not text.strip() for text in request.texts):
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "Embedding request requires non-empty texts.",
            )
        vectors = tuple(
            _hash_vector(text, dimensions=self._dimensions, language=request.language)
            for text in request.texts
        )
        return EmbeddingResult(
            vectors=vectors,
            dimensions=self._dimensions,
            provider=self.identity(),
            trace={"sdk_version": PROVIDER_SDK_VERSION, "trace_id": request.trace_id},
        )


class MockKnowledgeProvider(_MockBaseProvider):
    def __init__(
        self,
        documents: tuple[KnowledgeDocument, ...],
        *,
        name: str = "mock-knowledge",
        storage_policy: ProviderStoragePolicy | None = None,
    ) -> None:
        super().__init__(
            name=name,
            kind="knowledge",
            model_id="mock-knowledge-index",
            capabilities=ProviderCapabilities(
                supports_multilingual=True,
                capabilities=("search", "fetch_document"),
            ),
        )
        self._documents = {document.provider_document_id: document for document in documents}
        self._storage_policy = storage_policy or ProviderStoragePolicy()

    def storage_policy(self) -> ProviderStoragePolicy:
        return self._storage_policy

    async def search(self, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        if not request.query.strip():
            raise ProviderSDKError("PROVIDER_INPUT_INVALID", "Knowledge query is required.")
        terms = _terms(request.query)
        results: list[KnowledgeSearchResult] = []
        for document in self._documents.values():
            haystack = _terms(f"{document.title} {document.content}")
            overlap = len(terms & haystack)
            if overlap == 0:
                continue
            results.append(
                KnowledgeSearchResult(
                    provider_document_id=document.provider_document_id,
                    title=document.title,
                    snippet=document.content[:240],
                    score=overlap / max(1, len(terms)),
                    metadata=document.metadata,
                )
            )
        ranked = tuple(
            sorted(
                results,
                key=lambda result: (-result.score, result.provider_document_id),
            )[: request.limit]
        )
        return KnowledgeSearchResponse(
            results=ranked,
            provider=self.identity(),
            storage_policy=self._storage_policy,
            trace={"sdk_version": PROVIDER_SDK_VERSION, "trace_id": request.trace_id},
        )

    async def fetch_document(self, provider_document_id: str) -> KnowledgeDocument:
        document = self._documents.get(provider_document_id)
        if document is None:
            raise ProviderSDKError(
                "PROVIDER_RESPONSE_INVALID",
                "Knowledge document was not found in provider response.",
                status_code=404,
            )
        return document


class MockRerankerProvider(_MockBaseProvider):
    def __init__(self, *, name: str = "mock-reranker") -> None:
        super().__init__(
            name=name,
            kind="reranker",
            model_id="mock-overlap-reranker",
            capabilities=ProviderCapabilities(capabilities=("rerank",)),
        )

    async def rerank(self, request: RerankRequest) -> RerankResponse:
        terms = _terms(request.query)
        scored = []
        for document in request.documents:
            candidate_terms = _terms(f"{document.title} {document.snippet}")
            score = len(terms & candidate_terms) / max(1, len(terms))
            scored.append((score, document.provider_document_id, document))
        ranked = tuple(
            RerankResult(
                provider_document_id=document.provider_document_id,
                score=score,
                rank=index,
                metadata={"source_score": document.score},
            )
            for index, (score, _, document) in enumerate(
                sorted(scored, key=lambda item: (-item[0], item[1])),
                start=1,
            )
        )
        return RerankResponse(
            results=ranked,
            provider=self.identity(),
            trace={"sdk_version": PROVIDER_SDK_VERSION, "trace_id": request.trace_id},
        )


class MockVectorStoreProvider(_MockBaseProvider):
    def __init__(
        self,
        records: tuple[VectorRecord, ...] = (),
        *,
        name: str = "mock-vector-store",
    ) -> None:
        super().__init__(
            name=name,
            kind="vector_store",
            model_id="mock-memory-vector-store",
            capabilities=ProviderCapabilities(capabilities=("search", "upsert", "delete")),
        )
        self._records = {record.record_id: record for record in records}

    async def search(self, request: VectorSearchRequest) -> tuple[VectorSearchResult, ...]:
        if not request.vector:
            raise ProviderSDKError("PROVIDER_INPUT_INVALID", "Search vector is required.")
        scored = [
            (_cosine_similarity(request.vector, record.vector), record.record_id, record)
            for record in self._records.values()
            if _matches_filters(record.metadata, request.filters)
        ]
        return tuple(
            VectorSearchResult(record=record, score=score, rank=index)
            for index, (score, _, record) in enumerate(
                sorted(scored, key=lambda item: (-item[0], item[1]))[: request.limit],
                start=1,
            )
        )

    async def upsert(self, records: tuple[VectorRecord, ...]) -> int:
        for record in records:
            if not record.record_id or not record.vector:
                raise ProviderSDKError(
                    "PROVIDER_INPUT_INVALID",
                    "Vector records require a record_id and vector.",
                )
            self._records[record.record_id] = record
        return len(records)

    async def delete(self, record_ids: tuple[str, ...]) -> int:
        deleted = 0
        for record_id in record_ids:
            if self._records.pop(record_id, None) is not None:
                deleted += 1
        return deleted


def _token_count(text: str) -> int:
    return len([part for part in text.split() if part])


def _terms(text: str) -> set[str]:
    return {part.lower() for part in text.replace("\n", " ").split() if part.strip()}


def _hash_vector(text: str, *, dimensions: int, language: str) -> tuple[float, ...]:
    digest = hashlib.sha256(f"{language}:{text}".encode()).digest()
    values = tuple((digest[index % len(digest)] / 127.5) - 1.0 for index in range(dimensions))
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        return values
    return tuple(value / magnitude for value in values)


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot_product = sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )
    return dot_product / (left_norm * right_norm)


def _matches_filters(metadata: dict[str, object], filters: dict[str, object]) -> bool:
    return all(metadata.get(key) == value for key, value in filters.items())
