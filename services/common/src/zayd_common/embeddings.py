"""Embedding provider contracts and adapters for retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zayd_common.normalization import NORMALIZATION_FRAMEWORK_VERSION, normalize_text
from zayd_common.settings import ServiceSettings

EMBEDDING_INTERFACE_VERSION = "embedding-interface-v1"
LOCAL_HASH_EMBEDDING_PROVIDER_VERSION = "local-hash-embedding-v1"
OPENAI_COMPATIBLE_EMBEDDING_PROVIDER_VERSION = "openai-compatible-embedding-v1"
DEFAULT_LOCAL_EMBEDDING_MODEL = "local-hash-multilingual"
DEFAULT_LOCAL_EMBEDDING_DIMENSIONS = 128

EmbeddingProviderName = Literal["local", "openai_compatible"]
EmbeddingErrorCode = Literal[
    "EMBEDDING_EMPTY_INPUT",
    "EMBEDDING_PROVIDER_DISABLED",
    "EMBEDDING_PROVIDER_CONFIG_INVALID",
    "EMBEDDING_PROVIDER_UNAVAILABLE",
    "EMBEDDING_PROVIDER_TIMEOUT",
    "EMBEDDING_PROVIDER_AUTH_FAILED",
    "EMBEDDING_PROVIDER_RESPONSE_INVALID",
    "EMBEDDING_DIMENSION_MISMATCH",
]


class EmbeddingError(Exception):
    """Raised when embedding generation cannot complete safely."""

    def __init__(self, code: EmbeddingErrorCode, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class EmbeddingProviderInfo:
    provider_name: EmbeddingProviderName
    provider_version: str
    interface_version: str
    model_id: str
    model_revision: str | None
    dimensions: int
    normalization_enabled: bool
    normalization_framework_version: str | None
    batch_size: int
    timeout_seconds: int
    max_retries: int


@dataclass(frozen=True)
class EmbeddingVector:
    values: tuple[float, ...]
    text_index: int | None
    normalized_text: str
    dimensions: int


@dataclass(frozen=True)
class EmbeddingBatchResult:
    provider: EmbeddingProviderInfo
    vectors: tuple[EmbeddingVector, ...]


class EmbeddingProvider(Protocol):
    async def embed_documents(
        self,
        texts: tuple[str, ...],
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingBatchResult: ...

    async def embed_query(
        self,
        text: str,
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingVector: ...

    def provider_info(self) -> EmbeddingProviderInfo: ...


TransportResponse = tuple[int, bytes]
Transport = Callable[[str, dict[str, str], bytes, int], TransportResponse]


@dataclass(frozen=True)
class EmbeddingService:
    """High-level embedding interface with dimension validation."""

    provider: EmbeddingProvider
    expected_dimensions: int

    async def embed_documents(
        self,
        texts: tuple[str, ...],
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingBatchResult:
        non_empty = tuple(text for text in texts if text.strip())
        if not non_empty:
            raise EmbeddingError(
                "EMBEDDING_EMPTY_INPUT",
                "At least one non-empty text is required for embeddings.",
            )
        result = await self.provider.embed_documents(
            non_empty,
            language=language,
            normalize=normalize,
        )
        _validate_dimensions(result.provider.dimensions, self.expected_dimensions)
        for vector in result.vectors:
            _validate_dimensions(vector.dimensions, self.expected_dimensions)
        return result

    async def embed_query(
        self,
        text: str,
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingVector:
        if not text.strip():
            raise EmbeddingError(
                "EMBEDDING_EMPTY_INPUT",
                "A non-empty query is required for embeddings.",
            )
        vector = await self.provider.embed_query(text, language=language, normalize=normalize)
        _validate_dimensions(vector.dimensions, self.expected_dimensions)
        return vector


class LocalHashEmbeddingProvider:
    """Deterministic local embedding provider for self-hosted mode."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_LOCAL_EMBEDDING_MODEL,
        model_revision: str | None = LOCAL_HASH_EMBEDDING_PROVIDER_VERSION,
        dimensions: int = DEFAULT_LOCAL_EMBEDDING_DIMENSIONS,
        batch_size: int = 32,
        timeout_seconds: int = 1,
        max_retries: int = 0,
    ) -> None:
        self._provider = EmbeddingProviderInfo(
            provider_name="local",
            provider_version=LOCAL_HASH_EMBEDDING_PROVIDER_VERSION,
            interface_version=EMBEDDING_INTERFACE_VERSION,
            model_id=model_id,
            model_revision=model_revision,
            dimensions=dimensions,
            normalization_enabled=True,
            normalization_framework_version=NORMALIZATION_FRAMEWORK_VERSION,
            batch_size=batch_size,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def provider_info(self) -> EmbeddingProviderInfo:
        return self._provider

    async def embed_documents(
        self,
        texts: tuple[str, ...],
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingBatchResult:
        vectors = tuple(
            _local_vector(
                text,
                language=language,
                normalize=normalize,
                dimensions=self._provider.dimensions,
                index=index,
            )
            for index, text in enumerate(texts)
        )
        return EmbeddingBatchResult(provider=self._provider, vectors=vectors)

    async def embed_query(
        self,
        text: str,
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingVector:
        return _local_vector(
            text,
            language=language,
            normalize=normalize,
            dimensions=self._provider.dimensions,
            index=None,
        )


class OpenAICompatibleEmbeddingProvider:
    """OpenAI-compatible embeddings adapter with bounded retries."""

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        dimensions: int,
        model_revision: str | None = None,
        batch_size: int = 16,
        timeout_seconds: int = 20,
        max_retries: int = 1,
        api_key: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._dimensions = dimensions
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._api_key = api_key
        self._batch_size = batch_size
        self._transport = transport or _urlopen_transport
        self._provider = EmbeddingProviderInfo(
            provider_name="openai_compatible",
            provider_version=OPENAI_COMPATIBLE_EMBEDDING_PROVIDER_VERSION,
            interface_version=EMBEDDING_INTERFACE_VERSION,
            model_id=model_id,
            model_revision=model_revision,
            dimensions=dimensions,
            normalization_enabled=True,
            normalization_framework_version=NORMALIZATION_FRAMEWORK_VERSION,
            batch_size=batch_size,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def provider_info(self) -> EmbeddingProviderInfo:
        return self._provider

    async def embed_documents(
        self,
        texts: tuple[str, ...],
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingBatchResult:
        normalized_texts = tuple(
            _normalize_for_embedding(text, language=language, normalize=normalize)
            for text in texts
        )
        vectors: list[EmbeddingVector] = []
        for start in range(0, len(normalized_texts), self._batch_size):
            batch = normalized_texts[start : start + self._batch_size]
            batch_vectors = await self._request_batch(batch)
            for offset, values in enumerate(batch_vectors):
                vectors.append(
                    EmbeddingVector(
                        values=values,
                        text_index=start + offset,
                        normalized_text=batch[offset],
                        dimensions=len(values),
                    )
                )
        return EmbeddingBatchResult(provider=self._provider, vectors=tuple(vectors))

    async def embed_query(
        self,
        text: str,
        *,
        language: str,
        normalize: bool = True,
    ) -> EmbeddingVector:
        normalized_text = _normalize_for_embedding(text, language=language, normalize=normalize)
        values = (await self._request_batch((normalized_text,)))[0]
        return EmbeddingVector(
            values=values,
            text_index=None,
            normalized_text=normalized_text,
            dimensions=len(values),
        )

    async def _request_batch(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        payload = json.dumps({"input": list(texts), "model": self._model_id}).encode("utf-8")
        response = await self._post_with_retry(payload=payload, headers=headers)
        try:
            body = json.loads(response.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise EmbeddingError(
                "EMBEDDING_PROVIDER_RESPONSE_INVALID",
                "Embedding provider returned invalid JSON.",
                status_code=502,
            ) from exc
        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingError(
                "EMBEDDING_PROVIDER_RESPONSE_INVALID",
                "Embedding provider returned an invalid batch payload.",
                status_code=502,
            )
        ordered: list[tuple[float, ...] | None] = [None] * len(texts)
        for row in data:
            if not isinstance(row, dict):
                raise EmbeddingError(
                    "EMBEDDING_PROVIDER_RESPONSE_INVALID",
                    "Embedding provider returned a malformed result row.",
                    status_code=502,
                )
            index = row.get("index")
            embedding = row.get("embedding")
            if not isinstance(index, int) or not isinstance(embedding, list):
                raise EmbeddingError(
                    "EMBEDDING_PROVIDER_RESPONSE_INVALID",
                    "Embedding provider result is missing index or embedding values.",
                    status_code=502,
                )
            vector = tuple(float(value) for value in embedding)
            _validate_dimensions(len(vector), self._dimensions)
            ordered[index] = vector
        if any(vector is None for vector in ordered):
            raise EmbeddingError(
                "EMBEDDING_PROVIDER_RESPONSE_INVALID",
                "Embedding provider returned an incomplete batch.",
                status_code=502,
            )
        return tuple(vector for vector in ordered if vector is not None)

    async def _post_with_retry(self, *, payload: bytes, headers: dict[str, str]) -> bytes:
        endpoint = f"{self._base_url}/embeddings"
        last_error: EmbeddingError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                status_code, response = await asyncio.to_thread(
                    self._transport,
                    endpoint,
                    headers,
                    payload,
                    self._timeout_seconds,
                )
            except TimeoutError as exc:
                last_error = EmbeddingError(
                    "EMBEDDING_PROVIDER_TIMEOUT",
                    "Embedding provider timed out.",
                    status_code=504,
                )
                if attempt == self._max_retries:
                    raise last_error from exc
                continue
            except OSError as exc:
                last_error = EmbeddingError(
                    "EMBEDDING_PROVIDER_UNAVAILABLE",
                    "Embedding provider is unavailable.",
                    status_code=503,
                )
                if attempt == self._max_retries:
                    raise last_error from exc
                continue
            if status_code in {401, 403}:
                raise EmbeddingError(
                    "EMBEDDING_PROVIDER_AUTH_FAILED",
                    "Embedding provider rejected authentication.",
                    status_code=502,
                )
            if status_code == 429 or 500 <= status_code < 600:
                last_error = EmbeddingError(
                    "EMBEDDING_PROVIDER_UNAVAILABLE",
                    "Embedding provider returned a retryable error.",
                    status_code=503,
                )
                if attempt == self._max_retries:
                    raise last_error
                continue
            if status_code >= 400:
                raise EmbeddingError(
                    "EMBEDDING_PROVIDER_RESPONSE_INVALID",
                    "Embedding provider request failed.",
                    status_code=502,
                )
            return response
        raise last_error or EmbeddingError(
            "EMBEDDING_PROVIDER_UNAVAILABLE",
            "Embedding provider is unavailable.",
            status_code=503,
        )


def build_embedding_service(
    settings: ServiceSettings,
    *,
    transport: Transport | None = None,
) -> EmbeddingService:
    """Build an embedding service from runtime settings."""
    if settings.embedding_provider == "local":
        provider: EmbeddingProvider = LocalHashEmbeddingProvider(
            model_id=settings.embedding_model or DEFAULT_LOCAL_EMBEDDING_MODEL,
            model_revision=settings.embedding_revision,
            dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
        )
        return EmbeddingService(
            provider=provider,
            expected_dimensions=settings.embedding_dimensions,
        )

    if settings.embedding_provider == "openai_compatible":
        if not settings.enable_external_providers:
            raise EmbeddingError(
                "EMBEDDING_PROVIDER_DISABLED",
                "OpenAI-compatible embeddings require ENABLE_EXTERNAL_PROVIDERS=true.",
                status_code=400,
            )
        if settings.embedding_base_url is None or settings.embedding_model is None:
            raise EmbeddingError(
                "EMBEDDING_PROVIDER_CONFIG_INVALID",
                "OpenAI-compatible embeddings require EMBEDDING_BASE_URL and EMBEDDING_MODEL.",
                status_code=400,
            )
        provider = OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_base_url,
            model_id=settings.embedding_model,
            model_revision=settings.embedding_revision,
            dimensions=settings.embedding_dimensions,
            batch_size=settings.embedding_batch_size,
            timeout_seconds=settings.embedding_timeout_seconds,
            max_retries=settings.embedding_max_retries,
            api_key=(
                settings.embedding_api_key.get_secret_value()
                if settings.embedding_api_key is not None
                else None
            ),
            transport=transport,
        )
        return EmbeddingService(
            provider=provider,
            expected_dimensions=settings.embedding_dimensions,
        )

    raise EmbeddingError(
        "EMBEDDING_PROVIDER_CONFIG_INVALID",
        "Unsupported embedding provider configuration.",
        status_code=400,
    )


def _urlopen_transport(
    url: str,
    headers: dict[str, str],
    payload: bytes,
    timeout_seconds: int,
) -> TransportResponse:
    request = Request(url, data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            raise TimeoutError("embedding transport timed out") from exc
        raise OSError("transport failed") from exc


def _local_vector(
    text: str,
    *,
    language: str,
    normalize: bool,
    dimensions: int,
    index: int | None,
) -> EmbeddingVector:
    normalized_text = _normalize_for_embedding(text, language=language, normalize=normalize)
    values = [0.0] * dimensions
    tokens = _local_tokens(normalized_text)
    if not tokens:
        tokens = ("<empty>",)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0)
        values[bucket] += sign * weight
    norm = math.sqrt(sum(value * value for value in values))
    if norm > 0:
        values = [value / norm for value in values]
    return EmbeddingVector(
        values=tuple(values),
        text_index=index,
        normalized_text=normalized_text,
        dimensions=dimensions,
    )


def _local_tokens(text: str) -> tuple[str, ...]:
    words = tuple(part for part in text.split() if part)
    if words:
        return words
    if len(text) <= 3:
        return (text,)
    return tuple(text[index : index + 3] for index in range(len(text) - 2))


def _normalize_for_embedding(text: str, *, language: str, normalize: bool) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if not normalize:
        return stripped
    return normalize_text(stripped, language=language).normalized


def _validate_dimensions(actual: int, expected: int) -> None:
    if actual != expected:
        raise EmbeddingError(
            "EMBEDDING_DIMENSION_MISMATCH",
            f"Embedding dimensions {actual} do not match expected dimension {expected}.",
        )
