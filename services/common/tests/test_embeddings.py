"""Tests for embedding provider contracts and adapters."""

from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import SecretStr
from zayd_common.embeddings import (
    DEFAULT_LOCAL_EMBEDDING_DIMENSIONS,
    DEFAULT_LOCAL_EMBEDDING_MODEL,
    EMBEDDING_INTERFACE_VERSION,
    EmbeddingError,
    EmbeddingService,
    LocalHashEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_service,
)
from zayd_common.settings import ServiceSettings


def test_local_embedding_provider_is_deterministic_and_normalized() -> None:
    provider = LocalHashEmbeddingProvider()

    result = asyncio.run(
        provider.embed_documents(
            ("  ข้อความ ทดสอบ  ", "اختبار الكتاب"),
            language="th",
        )
    )

    assert result.provider.interface_version == EMBEDDING_INTERFACE_VERSION
    assert result.provider.model_id == DEFAULT_LOCAL_EMBEDDING_MODEL
    assert result.provider.dimensions == DEFAULT_LOCAL_EMBEDDING_DIMENSIONS
    assert len(result.vectors) == 2
    assert result.vectors[0].text_index == 0
    assert result.vectors[0].normalized_text == "ข้อความ ทดสอบ"
    assert len(result.vectors[0].values) == DEFAULT_LOCAL_EMBEDDING_DIMENSIONS

    repeat = asyncio.run(
        provider.embed_query("ข้อความ ทดสอบ", language="th")
    )
    assert repeat.values == result.vectors[0].values


def test_embedding_service_detects_dimension_mismatch_before_use() -> None:
    provider = LocalHashEmbeddingProvider(dimensions=64)
    service = EmbeddingService(provider=provider, expected_dimensions=128)

    with pytest.raises(EmbeddingError) as exc:
        asyncio.run(service.embed_query("test text", language="en"))

    assert exc.value.code == "EMBEDDING_DIMENSION_MISMATCH"


def test_build_embedding_service_supports_local_mode_without_external_dependencies() -> None:
    settings = ServiceSettings(
        app_name="retrieval",
        embedding_provider="local",
        embedding_dimensions=96,
        embedding_batch_size=8,
    )

    service = build_embedding_service(settings)
    result = asyncio.run(service.embed_documents(("alpha", "beta"), language="en"))

    assert result.provider.provider_name == "local"
    assert result.provider.dimensions == 96
    assert len(result.vectors) == 2


def test_openai_compatible_provider_batches_and_retries() -> None:
    calls: list[bytes] = []

    def flaky_transport(url: str, headers: dict[str, str], payload: bytes, timeout: int):
        calls.append(payload)
        if len(calls) == 1:
            return 503, b'{"error":"retry"}'
        body = json.loads(payload.decode("utf-8"))
        data = [
            {"index": index, "embedding": [float(index + 1), 0.5, 0.25]}
            for index, _ in enumerate(body["input"])
        ]
        return 200, json.dumps({"data": data}).encode("utf-8")

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embeddings.local/v1",
        model_id="text-embedding-demo",
        dimensions=3,
        batch_size=2,
        max_retries=1,
        transport=flaky_transport,
    )

    result = asyncio.run(
        provider.embed_documents(("one", "two", "three"), language="en")
    )

    assert len(calls) == 3
    assert len(result.vectors) == 3
    assert result.vectors[2].text_index == 2
    assert result.vectors[0].dimensions == 3


def test_openai_compatible_provider_surfaces_dimension_mismatch() -> None:
    def bad_dimensions(url: str, headers: dict[str, str], payload: bytes, timeout: int):
        return 200, json.dumps({"data": [{"index": 0, "embedding": [0.1, 0.2]}]}).encode("utf-8")

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://embeddings.local/v1",
        model_id="text-embedding-demo",
        dimensions=3,
        transport=bad_dimensions,
    )

    with pytest.raises(EmbeddingError) as exc:
        asyncio.run(provider.embed_query("one", language="en"))

    assert exc.value.code == "EMBEDDING_DIMENSION_MISMATCH"


def test_build_embedding_service_requires_external_provider_configuration() -> None:
    with pytest.raises(ValueError, match="ENABLE_EXTERNAL_PROVIDERS=false"):
        ServiceSettings(
            app_name="retrieval",
            embedding_provider="openai_compatible",
            embedding_base_url="http://embeddings.local/v1",
            embedding_model="text-embedding-demo",
        )

    with pytest.raises(ValueError, match="EMBEDDING_BASE_URL is required"):
        ServiceSettings(
            app_name="retrieval",
            enable_external_providers=True,
            embedding_provider="openai_compatible",
            embedding_model="text-embedding-demo",
        )


def test_build_embedding_service_openai_mode_uses_runtime_settings() -> None:
    settings = ServiceSettings(
        app_name="retrieval",
        enable_external_providers=True,
        embedding_provider="openai_compatible",
        embedding_base_url="http://embeddings.local/v1",
        embedding_api_key=SecretStr("test-key"),
        embedding_model="text-embedding-demo",
        embedding_revision="2026-07",
        embedding_dimensions=3,
        embedding_batch_size=4,
        embedding_timeout_seconds=9,
        embedding_max_retries=1,
    )

    service = build_embedding_service(
        settings,
        transport=lambda url, headers, payload, timeout: (
            200,
            json.dumps({"data": [{"index": 0, "embedding": [1.0, 0.0, 0.0]}]}).encode("utf-8"),
        ),
    )

    result = asyncio.run(service.embed_query("test", language="en"))

    assert result.dimensions == 3
