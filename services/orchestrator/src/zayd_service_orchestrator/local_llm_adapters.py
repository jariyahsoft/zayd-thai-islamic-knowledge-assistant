"""Local LLM adapters for Ollama and vLLM using OpenAI-compatible endpoints."""

from __future__ import annotations

from zayd_service_orchestrator.openai_llm_adapter import OpenAICompatibleLLMAdapter


class OllamaLLMAdapter(OpenAICompatibleLLMAdapter):
    """
    Ollama LLM adapter using OpenAI-compatible API.

    Ollama exposes an OpenAI-compatible endpoint at /v1/chat/completions
    when started with the appropriate flags.
    """

    def __init__(
        self,
        *,
        provider_name: str = "ollama",
        base_url: str = "http://localhost:11434/v1",
        model_id: str = "llama2",
        timeout_ms: int = 60_000,
        max_retries: int = 1,
        max_input_tokens: int = 4_096,
        max_output_tokens: int = 2_048,
    ) -> None:
        """
        Initialize Ollama LLM adapter.

        Args:
            provider_name: Provider name for registry
            base_url: Ollama API base URL (default: http://localhost:11434/v1)
            model_id: Ollama model name (e.g., "llama2", "mistral", "phi")
            timeout_ms: Request timeout in milliseconds (default: 60s for local models)
            max_retries: Maximum retry attempts (default: 1 for local)
            max_input_tokens: Maximum input context tokens
            max_output_tokens: Maximum output tokens
        """
        super().__init__(
            provider_name=provider_name,
            base_url=base_url,
            api_key=None,  # Ollama doesn't require API keys
            model_id=model_id,
            timeout_ms=timeout_ms,
            max_retries=max_retries,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
        )


class VLLMLLMAdapter(OpenAICompatibleLLMAdapter):
    """
    vLLM LLM adapter using OpenAI-compatible API.

    vLLM server exposes an OpenAI-compatible /v1/chat/completions endpoint
    when started with --api-key or without authentication.
    """

    def __init__(
        self,
        *,
        provider_name: str = "vllm",
        base_url: str = "http://localhost:8000/v1",
        api_key: str | None = None,
        model_id: str,
        timeout_ms: int = 60_000,
        max_retries: int = 1,
        max_input_tokens: int = 4_096,
        max_output_tokens: int = 2_048,
    ) -> None:
        """
        Initialize vLLM LLM adapter.

        Args:
            provider_name: Provider name for registry
            base_url: vLLM API base URL (default: http://localhost:8000/v1)
            api_key: Optional API key if vLLM server requires authentication
            model_id: Model identifier (must match vLLM server's loaded model)
            timeout_ms: Request timeout in milliseconds (default: 60s for local models)
            max_retries: Maximum retry attempts (default: 1 for local)
            max_input_tokens: Maximum input context tokens
            max_output_tokens: Maximum output tokens
        """
        super().__init__(
            provider_name=provider_name,
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            timeout_ms=timeout_ms,
            max_retries=max_retries,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
        )


# Type aliases for protocol compatibility
OllamaLLMProvider = OllamaLLMAdapter
VLLMLLMProvider = VLLMLLMAdapter
