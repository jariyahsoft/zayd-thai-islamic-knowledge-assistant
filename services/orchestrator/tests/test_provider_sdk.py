import pytest
from zayd_service_orchestrator.provider_sdk import (
    AllowListedProviderRegistry,
    EmbeddingRequest,
    KnowledgeDocument,
    KnowledgeSearchRequest,
    LLMMessage,
    LLMRequest,
    MockEmbeddingProvider,
    MockKnowledgeProvider,
    MockLLMProvider,
    MockRerankerProvider,
    MockVectorStoreProvider,
    ProviderConfig,
    ProviderSDKError,
    RerankRequest,
    VectorRecord,
    VectorSearchRequest,
)


@pytest.mark.asyncio
async def test_mock_llm_is_deterministic_and_supports_streaming() -> None:
    provider = MockLLMProvider()
    request = LLMRequest(
        messages=(LLMMessage(role="user", content="What is wudu?"),),
        trace_id="trace-123",
    )

    first = await provider.generate(request)
    second = await provider.generate(request)
    streamed = [chunk async for chunk in provider.stream(request)]

    assert first.text == second.text
    assert first.provider.kind == "llm"
    assert first.usage.total_tokens > 0
    assert streamed
    assert first.trace["trace_id"] == "trace-123"


@pytest.mark.asyncio
async def test_mock_embedding_returns_configured_dimensions() -> None:
    provider = MockEmbeddingProvider(dimensions=4)

    result = await provider.embed(
        EmbeddingRequest(texts=("ภาษาไทย", "Arabic text"), language="th")
    )

    assert result.dimensions == 4
    assert len(result.vectors) == 2
    assert all(len(vector) == 4 for vector in result.vectors)


@pytest.mark.asyncio
async def test_knowledge_provider_search_fetch_and_rerank_are_deterministic() -> None:
    knowledge_provider = MockKnowledgeProvider(
        documents=(
            KnowledgeDocument(
                provider_document_id="doc-1",
                title="Prayer evidence",
                content="prayer wudu intention",
            ),
            KnowledgeDocument(
                provider_document_id="doc-2",
                title="Fasting evidence",
                content="fasting Ramadan",
            ),
        )
    )
    reranker = MockRerankerProvider()

    search = await knowledge_provider.search(KnowledgeSearchRequest(query="prayer wudu"))
    reranked = await reranker.rerank(
        RerankRequest(query="wudu prayer", documents=search.results)
    )
    document = await knowledge_provider.fetch_document("doc-1")

    assert [result.provider_document_id for result in search.results] == ["doc-1"]
    assert reranked.results[0].provider_document_id == "doc-1"
    assert document.title == "Prayer evidence"


@pytest.mark.asyncio
async def test_vector_store_upsert_search_delete() -> None:
    provider = MockVectorStoreProvider()

    inserted = await provider.upsert(
        (
            VectorRecord(
                record_id="a",
                vector=(1.0, 0.0),
                metadata={"language": "th"},
            ),
            VectorRecord(
                record_id="b",
                vector=(0.0, 1.0),
                metadata={"language": "ar"},
            ),
        )
    )
    results = await provider.search(
        VectorSearchRequest(vector=(1.0, 0.0), filters={"language": "th"})
    )
    deleted = await provider.delete(("a", "missing"))

    assert inserted == 2
    assert results[0].record.record_id == "a"
    assert deleted == 1


def test_registry_loads_only_explicitly_allowed_enabled_providers() -> None:
    registry = AllowListedProviderRegistry()
    registry.register(MockLLMProvider(name="allowed"))
    registry.register(MockLLMProvider(name="disabled"), enabled=False)

    assert registry.allowed_provider_names("llm") == ("allowed",)
    assert registry.load("llm", "allowed").identity().name == "allowed"

    with pytest.raises(ProviderSDKError) as disabled:
        registry.load("llm", "disabled")
    with pytest.raises(ProviderSDKError) as unknown:
        registry.load("llm", "not-registered")

    assert disabled.value.code == "PROVIDER_DISABLED"
    assert unknown.value.code == "PROVIDER_NOT_ALLOWED"


def test_provider_config_validation_is_stable() -> None:
    provider = MockLLMProvider()

    valid = provider.validate_config(ProviderConfig(provider_name="mock-llm", kind="llm"))
    invalid = provider.validate_config(
        ProviderConfig(
            provider_name="other",
            kind="embedding",
            enabled=False,
            timeout_ms=0,
            max_retries=9,
        )
    )

    assert valid.valid is True
    assert invalid.valid is False
    assert len(invalid.errors) == 5
