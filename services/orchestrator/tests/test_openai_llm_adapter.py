"""Tests for OpenAI-compatible LLM adapter."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from zayd_common.telemetry import telemetry_registry
from zayd_service_orchestrator.openai_llm_adapter import OpenAICompatibleLLMAdapter
from zayd_service_orchestrator.provider_sdk import (
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    ProviderSDKError,
)


def mock_openai_response(
    content: str = "Test response",
    finish_reason: str = "stop",
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Create a mock OpenAI API response."""
    if usage is None:
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_generate_success() -> None:
    """Test successful generation with OpenAI adapter."""
    telemetry_registry.reset()
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model_id="gpt-3.5-turbo",
    )

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response())
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="What is prayer?"),),
        trace_id="trace-123",
    )

    response = await adapter.generate(request)

    assert response.text == "Test response"
    assert response.finish_reason == "stop"
    assert response.usage.total_tokens == 15
    assert response.provider.kind == "llm"
    assert response.trace["trace_id"] == "trace-123"
    exported = telemetry_registry.export_prometheus_text()
    assert "provider_generate_total" in exported
    assert 'status="ok"' in exported


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_streaming() -> None:
    """Test streaming with OpenAI adapter."""
    telemetry_registry.reset()
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    stream_data = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
        "data: [DONE]\n\n",
    ]

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, content="".join(stream_data))
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Say hello"),),
    )

    chunks = [chunk async for chunk in adapter.stream(request)]

    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_json_response_format() -> None:
    """Test JSON response format."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    json_content = '{"answer": "Prayer is obligatory"}'
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response(content=json_content))
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Explain prayer"),),
        response_format="json",
    )

    response = await adapter.generate(request)

    assert response.text == json_content
    # Verify JSON is valid
    assert json.loads(response.text)["answer"] == "Prayer is obligatory"


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_retry_on_500() -> None:
    """Test retry logic on 5xx errors."""
    telemetry_registry.reset()
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        max_retries=2,
    )

    mock_route = respx.post("https://api.openai.com/v1/chat/completions")
    mock_route.side_effect = [
        httpx.Response(500, json={"error": "Internal server error"}),
        httpx.Response(500, json={"error": "Internal server error"}),
        httpx.Response(200, json=mock_openai_response()),
    ]

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    response = await adapter.generate(request)

    assert response.text == "Test response"
    assert mock_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_no_retry_on_400() -> None:
    """Test no retry on 4xx errors."""
    telemetry_registry.reset()
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        max_retries=2,
    )

    mock_route = respx.post("https://api.openai.com/v1/chat/completions")
    mock_route.mock(return_value=httpx.Response(400, json={"error": "Bad request"}))

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    with pytest.raises(ProviderSDKError) as exc_info:
        await adapter.generate(request)

    assert exc_info.value.code == "PROVIDER_RESPONSE_INVALID"
    assert mock_route.call_count == 1
    exported = telemetry_registry.export_prometheus_text()
    assert "provider_generate_total" in exported
    assert 'status="http_error"' in exported


@pytest.mark.asyncio
async def test_openai_adapter_empty_messages() -> None:
    """Test validation of empty messages."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    request = LLMRequest(messages=())

    with pytest.raises(ProviderSDKError) as exc_info:
        await adapter.generate(request)

    assert exc_info.value.code == "PROVIDER_INPUT_INVALID"


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_malformed_response() -> None:
    """Test handling of malformed response."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"invalid": "response"})
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    with pytest.raises(ProviderSDKError) as exc_info:
        await adapter.generate(request)

    assert exc_info.value.code == "PROVIDER_RESPONSE_INVALID"
    assert "Failed to parse" in exc_info.value.message


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_health_check_ok() -> None:
    """Test successful health check."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    health = await adapter.health_check()

    assert health.status == "ok"
    assert health.provider_name == "openai-test"
    assert health.latency_ms is not None


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_health_check_degraded() -> None:
    """Test degraded health check."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    respx.get("https://api.openai.com/v1/models").mock(
        return_value=httpx.Response(403, json={"error": "Unauthorized"})
    )

    health = await adapter.health_check()

    assert health.status == "degraded"
    assert "403" in health.message


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_health_check_unavailable() -> None:
    """Test unavailable health check."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    respx.get("https://api.openai.com/v1/models").mock(side_effect=httpx.ConnectError)

    health = await adapter.health_check()

    assert health.status == "unavailable"
    assert "failed" in health.message.lower()


def test_openai_adapter_config_validation() -> None:
    """Test configuration validation."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    valid_config = ProviderConfig(
        provider_name="openai-test",
        kind="llm",
        enabled=True,
        base_url="https://api.openai.com/v1",
        secret_ref="env:OPENAI_API_KEY",
        timeout_ms=30_000,
        max_retries=2,
    )

    result = adapter.validate_config(valid_config)
    assert result.valid is True
    assert len(result.errors) == 0


def test_openai_adapter_config_validation_errors() -> None:
    """Test configuration validation with errors."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    invalid_config = ProviderConfig(
        provider_name="openai-test",
        kind="embedding",
        enabled=False,
        timeout_ms=500,
        max_retries=10,
    )

    result = adapter.validate_config(invalid_config)
    assert result.valid is False
    assert len(result.errors) == 5
    assert any("disabled" in err for err in result.errors)
    assert any("kind" in err for err in result.errors)
    assert any("base_url" in err for err in result.errors)
    assert any("timeout_ms" in err for err in result.errors)
    assert any("max_retries" in err for err in result.errors)


def test_openai_adapter_identity_and_capabilities() -> None:
    """Test provider identity and capabilities."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model_id="gpt-4",
        max_input_tokens=32_000,
        max_output_tokens=8_000,
    )

    identity = adapter.identity()
    assert identity.name == "openai-test"
    assert identity.kind == "llm"
    assert identity.model_id == "gpt-4"
    assert identity.version == "openai-compatible-v1"

    capabilities = adapter.capabilities()
    assert capabilities.supports_streaming is True
    assert capabilities.supports_structured_output is True
    assert capabilities.max_input_tokens == 32_000
    assert capabilities.max_output_tokens == 8_000


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_masks_api_key_in_errors() -> None:
    """Test that API keys are not exposed in error messages."""
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="sk-secret-key-12345",
    )

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    with pytest.raises(ProviderSDKError) as exc_info:
        await adapter.generate(request)

    error_message = str(exc_info.value)
    assert "sk-secret-key-12345" not in error_message


@pytest.mark.asyncio
@respx.mock
async def test_openai_adapter_records_provider_span() -> None:
    adapter = OpenAICompatibleLLMAdapter(
        provider_name="openai-test",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response())
    )

    await adapter.generate(
        LLMRequest(
            messages=(LLMMessage(role="user", content="Explain prayer"),),
            trace_id="trace-provider-span",
        )
    )

    spans = telemetry_registry.spans()
    assert any(
        span.name == "provider.generate"
        and span.attributes.get("provider_name") == "openai-test"
        for span in spans
    )
