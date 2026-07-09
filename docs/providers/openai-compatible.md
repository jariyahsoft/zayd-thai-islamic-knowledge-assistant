# OpenAI-Compatible LLM Provider

The OpenAI-compatible LLM adapter connects to OpenAI API, Azure OpenAI, and
OpenAI-compatible endpoints (vLLM, llama.cpp, LocalAI, etc.).

## Supported Features

- Text generation with configurable temperature and max tokens
- Streaming responses via Server-Sent Events
- Structured JSON output via `response_format`
- Automatic retry on 5xx errors (up to 2 retries by default)
- Request timeout and cancellation
- Health checks via `/models` endpoint
- Usage tracking (input/output/total tokens)

## Configuration

```python
from zayd_service_orchestrator import OpenAICompatibleLLMAdapter

adapter = OpenAICompatibleLLMAdapter(
    provider_name="openai",
    base_url="https://api.openai.com/v1",
    api_key="sk-...",  # or None for local endpoints
    model_id="gpt-3.5-turbo",
    timeout_ms=30_000,
    max_retries=2,
    max_input_tokens=8_192,
    max_output_tokens=4_096,
)
```

## Registry Integration

```python
from zayd_service_orchestrator import AllowListedProviderRegistry

registry = AllowListedProviderRegistry()
registry.register(adapter, enabled=True)

# Load provider by name
provider = registry.load("llm", "openai")
```

## OpenAI API Compatibility

The adapter follows OpenAI's `/chat/completions` API format:

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "user", "content": "What is wudu?"}
  ],
  "temperature": 0.0,
  "max_tokens": 512,
  "stream": false
}
```

## Azure OpenAI Configuration

For Azure OpenAI, set the base URL to your Azure endpoint:

```python
adapter = OpenAICompatibleLLMAdapter(
    provider_name="azure-openai",
    base_url="https://<resource>.openai.azure.com/openai/deployments/<deployment>",
    api_key="<azure-api-key>",
    model_id="<deployment-name>",
)
```

## Local Endpoints

For local endpoints (vLLM, llama.cpp server, Ollama with OpenAI compatibility):

```python
adapter = OpenAICompatibleLLMAdapter(
    provider_name="vllm-local",
    base_url="http://localhost:8000/v1",
    api_key=None,  # No API key required
    model_id="meta-llama/Llama-2-7b-chat-hf",
)
```

## Error Handling

The adapter raises `ProviderSDKError` with stable error codes:

- `PROVIDER_INPUT_INVALID`: Empty messages or invalid request
- `PROVIDER_RESPONSE_INVALID`: Malformed response, HTTP errors, timeout
- `PROVIDER_CONFIG_INVALID`: Invalid configuration
- `PROVIDER_DISABLED`: Provider is disabled in registry

## Security

- API keys are never logged or exposed in error messages
- Secrets should be stored in `ProviderConfig.secret_ref`, not inline
- Request traces exclude credentials and hidden reasoning
- Timeout and retry bounds are enforced

## Streaming Cancellation

Streaming requests can be cancelled by breaking out of the async iteration:

```python
async for chunk in adapter.stream(request):
    if should_stop:
        break  # Closes HTTP connection
```

## Health Checks

Health checks hit the `/models` endpoint with a 5-second timeout:

```python
health = await adapter.health_check()
# health.status: "ok" | "degraded" | "unavailable"
```
