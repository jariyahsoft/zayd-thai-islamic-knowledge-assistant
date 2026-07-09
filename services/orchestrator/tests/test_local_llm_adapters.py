"""Tests for local LLM adapters (Ollama and vLLM)."""

from __future__ import annotations

import httpx
import pytest
import respx
from zayd_service_orchestrator.local_llm_adapters import (
    OllamaLLMAdapter,
    VLLMLLMAdapter,
)
from zayd_service_orchestrator.provider_sdk import LLMMessage, LLMRequest


def mock_openai_response() -> dict[str, object]:
    """Create a mock OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "llama2",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


@pytest.mark.asyncio
@respx.mock
async def test_ollama_adapter_defaults() -> None:
    """Test Ollama adapter with default configuration."""
    adapter = OllamaLLMAdapter(model_id="llama2")

    assert adapter.identity().name == "ollama"
    assert adapter.identity().model_id == "llama2"
    assert adapter.capabilities().max_input_tokens == 4_096

    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response())
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    response = await adapter.generate(request)

    assert response.text == "Test response"
    assert response.provider.name == "ollama"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_adapter_custom_base_url() -> None:
    """Test Ollama adapter with custom base URL."""
    adapter = OllamaLLMAdapter(
        base_url="http://custom-ollama:11434/v1",
        model_id="mistral",
    )

    respx.post("http://custom-ollama:11434/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response())
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    response = await adapter.generate(request)

    assert response.text == "Test response"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_adapter_health_check() -> None:
    """Test Ollama adapter health check."""
    adapter = OllamaLLMAdapter()

    respx.get("http://localhost:11434/v1/models").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    health = await adapter.health_check()

    assert health.status == "ok"
    assert health.provider_name == "ollama"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_adapter_health_check_unavailable() -> None:
    """Test Ollama adapter health check when Ollama is unavailable."""
    adapter = OllamaLLMAdapter()

    respx.get("http://localhost:11434/v1/models").mock(side_effect=httpx.ConnectError)

    health = await adapter.health_check()

    assert health.status == "unavailable"
    assert "failed" in health.message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_vllm_adapter_defaults() -> None:
    """Test vLLM adapter with default configuration."""
    adapter = VLLMLLMAdapter(model_id="meta-llama/Llama-2-7b-chat-hf")

    assert adapter.identity().name == "vllm"
    assert adapter.identity().model_id == "meta-llama/Llama-2-7b-chat-hf"
    assert adapter.capabilities().max_input_tokens == 4_096

    respx.post("http://localhost:8000/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_openai_response())
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    response = await adapter.generate(request)

    assert response.text == "Test response"
    assert response.provider.name == "vllm"


@pytest.mark.asyncio
@respx.mock
async def test_vllm_adapter_with_api_key() -> None:
    """Test vLLM adapter with API key authentication."""
    adapter = VLLMLLMAdapter(
        api_key="vllm-secret-key",
        model_id="meta-llama/Llama-2-7b-chat-hf",
    )

    mock_route = respx.post("http://localhost:8000/v1/chat/completions")
    mock_route.mock(return_value=httpx.Response(200, json=mock_openai_response()))

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    await adapter.generate(request)

    # Verify Authorization header was sent
    assert mock_route.calls.last.request.headers["Authorization"] == "Bearer vllm-secret-key"


@pytest.mark.asyncio
@respx.mock
async def test_vllm_adapter_health_check() -> None:
    """Test vLLM adapter health check."""
    adapter = VLLMLLMAdapter(model_id="test-model")

    respx.get("http://localhost:8000/v1/models").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    health = await adapter.health_check()

    assert health.status == "ok"
    assert health.provider_name == "vllm"


@pytest.mark.asyncio
@respx.mock
async def test_local_adapters_no_api_key_in_errors() -> None:
    """Test that local adapters don't expose internal errors."""
    adapter = OllamaLLMAdapter()

    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )

    request = LLMRequest(
        messages=(LLMMessage(role="user", content="Test"),),
    )

    with pytest.raises(Exception) as exc_info:
        await adapter.generate(request)

    error_message = str(exc_info.value)
    # Should contain error info but not expose internal paths
    assert "HTTP 500" in error_message or "PROVIDER_RESPONSE_INVALID" in str(exc_info.value.args[0])
