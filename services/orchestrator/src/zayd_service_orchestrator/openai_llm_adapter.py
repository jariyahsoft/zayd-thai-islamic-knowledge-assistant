"""OpenAI-compatible LLM adapter with streaming, structured output, and retry support."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import httpx
from zayd_common.telemetry import telemetry_registry

from zayd_service_orchestrator.provider_sdk import (
    PROVIDER_SDK_VERSION,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ProviderCapabilities,
    ProviderConfig,
    ProviderHealth,
    ProviderIdentity,
    ProviderSDKError,
    ProviderValidationResult,
)


class OpenAICompatibleLLMAdapter:
    """
    OpenAI-compatible LLM adapter supporting streaming, structured output, and retry.

    Compatible with OpenAI API, Azure OpenAI, and OpenAI-compatible endpoints
    (e.g., vLLM, llama.cpp, LocalAI).
    """

    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str | None = None,
        model_id: str = "gpt-3.5-turbo",
        timeout_ms: int = 30_000,
        max_retries: int = 2,
        max_input_tokens: int = 8_192,
        max_output_tokens: int = 4_096,
    ) -> None:
        """
        Initialize OpenAI-compatible LLM adapter.

        Args:
            provider_name: Provider name for registry
            base_url: Base URL for API (e.g., https://api.openai.com/v1)
            api_key: API key for authentication (optional for local endpoints)
            model_id: Model identifier
            timeout_ms: Request timeout in milliseconds
            max_retries: Maximum retry attempts
            max_input_tokens: Maximum input context tokens
            max_output_tokens: Maximum output tokens
        """
        self._provider_name = provider_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_id = model_id
        self._timeout_ms = timeout_ms
        self._max_retries = max_retries
        self._max_input_tokens = max_input_tokens
        self._max_output_tokens = max_output_tokens

    def identity(self) -> ProviderIdentity:
        """Return provider identity metadata."""
        return ProviderIdentity(
            name=self._provider_name,
            kind="llm",
            version="openai-compatible-v1",
            api_version=PROVIDER_SDK_VERSION,
            model_id=self._model_id,
            model_revision=None,
        )

    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        return ProviderCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            supports_batching=False,
            supports_multilingual=True,
            supports_health_check=True,
            max_input_tokens=self._max_input_tokens,
            max_output_tokens=self._max_output_tokens,
            capabilities=("generate", "stream"),
        )

    def validate_config(self, config: ProviderConfig) -> ProviderValidationResult:
        """Validate provider configuration."""
        errors: list[str] = []
        warnings: list[str] = []

        if not config.enabled:
            errors.append("provider config is disabled")
        if config.kind != "llm":
            errors.append(f"provider kind must be 'llm', got '{config.kind}'")
        if not config.base_url:
            errors.append("base_url is required for OpenAI-compatible adapter")
        if config.timeout_ms < 1_000 or config.timeout_ms > 300_000:
            errors.append("timeout_ms must be between 1000 and 300000")
        if config.max_retries < 0 or config.max_retries > 5:
            errors.append("max_retries must be between 0 and 5")

        if not config.secret_ref and config.base_url and "localhost" not in config.base_url:
            warnings.append("secret_ref not set for remote endpoint")

        return ProviderValidationResult(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    async def health_check(self) -> ProviderHealth:
        """Perform health check against the provider."""
        checked_at = datetime.now(UTC)
        with telemetry_registry.span(
            "provider.health_check",
            attributes={"provider_name": self._provider_name, "provider_kind": "llm"},
        ):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    headers = self._build_headers()
                    response = await client.get(
                        f"{self._base_url}/models",
                        headers=headers,
                    )
                    if response.status_code == 200:
                        latency_ms = (datetime.now(UTC) - checked_at).total_seconds() * 1000
                        telemetry_registry.record_counter(
                            "provider_health_total",
                            provider=self._provider_name,
                            kind="llm",
                            status="ok",
                        )
                        telemetry_registry.record_histogram(
                            "provider_health_latency_ms",
                            latency_ms,
                            provider=self._provider_name,
                            kind="llm",
                        )
                        return ProviderHealth(
                            status="ok",
                            checked_at=checked_at,
                            provider_name=self._provider_name,
                            kind="llm",
                            sdk_version=PROVIDER_SDK_VERSION,
                            message="Provider endpoint is reachable",
                            latency_ms=latency_ms,
                            trace={"provider_name": self._provider_name},
                        )
                    telemetry_registry.record_counter(
                        "provider_health_total",
                        provider=self._provider_name,
                        kind="llm",
                        status="degraded",
                    )
                    return ProviderHealth(
                        status="degraded",
                        checked_at=checked_at,
                        provider_name=self._provider_name,
                        kind="llm",
                        sdk_version=PROVIDER_SDK_VERSION,
                        message=f"Provider returned status {response.status_code}",
                        trace={"provider_name": self._provider_name},
                    )
            except Exception as error:
                telemetry_registry.record_counter(
                    "provider_health_total",
                    provider=self._provider_name,
                    kind="llm",
                    status="unavailable",
                )
                return ProviderHealth(
                    status="unavailable",
                    checked_at=checked_at,
                    provider_name=self._provider_name,
                    kind="llm",
                    sdk_version=PROVIDER_SDK_VERSION,
                    message=f"Health check failed: {type(error).__name__}",
                    trace={"provider_name": self._provider_name},
                )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate LLM response using OpenAI-compatible API."""
        if not request.messages:
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "At least one message is required.",
            )

        payload = self._build_payload(request, stream=False)

        with telemetry_registry.span(
            "provider.generate",
            attributes={
                "provider_name": self._provider_name,
                "provider_kind": "llm",
                "trace_id": request.trace_id,
            },
        ):
            started_at = perf_counter()
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout_ms / 1000.0,
                ) as client:
                    for attempt in range(self._max_retries + 1):
                        try:
                            response = await client.post(
                                f"{self._base_url}/chat/completions",
                                json=payload,
                                headers=self._build_headers(),
                            )
                            response.raise_for_status()
                            parsed = self._parse_response(response.json(), request)
                            telemetry_registry.record_counter(
                                "provider_generate_total",
                                provider=self._provider_name,
                                model=self._model_id,
                                status="ok",
                            )
                            telemetry_registry.record_histogram(
                                "provider_generate_latency_ms",
                                (perf_counter() - started_at) * 1000,
                                provider=self._provider_name,
                                model=self._model_id,
                            )
                            if parsed.usage is not None:
                                telemetry_registry.record_histogram(
                                    "provider_tokens_total",
                                    float(parsed.usage.total_tokens),
                                    provider=self._provider_name,
                                    model=self._model_id,
                                )
                            return parsed
                        except httpx.HTTPStatusError as error:
                            if attempt == self._max_retries or error.response.status_code < 500:
                                raise
                            continue
                raise ProviderSDKError(
                    "PROVIDER_RESPONSE_INVALID",
                    "All retry attempts failed",
                    status_code=500,
                )
            except httpx.HTTPStatusError as error:
                telemetry_registry.record_counter(
                    "provider_generate_total",
                    provider=self._provider_name,
                    model=self._model_id,
                    status="http_error",
                )
                raise ProviderSDKError(
                    "PROVIDER_RESPONSE_INVALID",
                    f"HTTP {error.response.status_code}: {error.response.text[:200]}",
                    status_code=error.response.status_code,
                ) from error
            except httpx.TimeoutException as error:
                telemetry_registry.record_counter(
                    "provider_generate_total",
                    provider=self._provider_name,
                    model=self._model_id,
                    status="timeout",
                )
                raise ProviderSDKError(
                    "PROVIDER_RESPONSE_INVALID",
                    "Request timeout exceeded.",
                    status_code=504,
                ) from error
            except ProviderSDKError:
                telemetry_registry.record_counter(
                    "provider_generate_total",
                    provider=self._provider_name,
                    model=self._model_id,
                    status="provider_error",
                )
                raise
            except Exception as error:
                telemetry_registry.record_counter(
                    "provider_generate_total",
                    provider=self._provider_name,
                    model=self._model_id,
                    status="error",
                )
                raise ProviderSDKError(
                    "PROVIDER_RESPONSE_INVALID",
                    f"Request failed: {type(error).__name__}",
                    status_code=500,
                ) from error

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream LLM response using OpenAI-compatible API."""
        if not request.messages:
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "At least one message is required.",
            )

        payload = self._build_payload(request, stream=True)

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_ms / 1000.0,
            ) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=self._build_headers(),
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as error:
            raise ProviderSDKError(
                "PROVIDER_RESPONSE_INVALID",
                f"HTTP {error.response.status_code}",
                status_code=error.response.status_code,
            ) from error
        except httpx.TimeoutException as error:
            raise ProviderSDKError(
                "PROVIDER_RESPONSE_INVALID",
                "Stream timeout exceeded.",
                status_code=504,
            ) from error

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _build_payload(self, request: LLMRequest, *, stream: bool) -> dict[str, Any]:
        """Build OpenAI API request payload."""
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        payload: dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": min(request.max_output_tokens, self._max_output_tokens),
            "stream": stream,
        }

        if request.response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        return payload

    def _parse_response(self, data: dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Parse OpenAI API response."""
        try:
            choice = data["choices"][0]
            message = choice["message"]
            text = message.get("content", "")
            finish_reason = choice.get("finish_reason", "stop")

            usage_data = data.get("usage", {})
            usage = LLMUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Map OpenAI finish reasons to SDK finish reasons
            finish_reason_map = {
                "stop": "stop",
                "length": "length",
                "tool_calls": "tool_call",
                "content_filter": "error",
                "null": "stop",
            }
            mapped_finish_reason = finish_reason_map.get(finish_reason, "stop")

            return LLMResponse(
                text=text,
                finish_reason=mapped_finish_reason,  # type: ignore
                provider=self.identity(),
                usage=usage,
                trace={
                    "sdk_version": PROVIDER_SDK_VERSION,
                    "trace_id": request.trace_id,
                    "model": data.get("model"),
                    "finish_reason_raw": finish_reason,
                },
            )
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderSDKError(
                "PROVIDER_RESPONSE_INVALID",
                f"Failed to parse provider response: {type(error).__name__}",
            ) from error


# Type alias to satisfy LLMProvider protocol
OpenAICompatibleLLMProvider = OpenAICompatibleLLMAdapter
