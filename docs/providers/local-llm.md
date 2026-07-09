# Local LLM Providers

Local LLM adapters enable self-hosted operation without cloud LLM credentials.
Both Ollama and vLLM expose OpenAI-compatible APIs.

## Ollama Adapter

Ollama is a lightweight LLM runtime for running models locally on macOS, Linux,
and Windows.

### Configuration

```python
from zayd_service_orchestrator import OllamaLLMAdapter

adapter = OllamaLLMAdapter(
    provider_name="ollama",
    base_url="http://localhost:11434/v1",
    model_id="llama2",
    timeout_ms=60_000,
    max_retries=1,
    max_input_tokens=4_096,
    max_output_tokens=2_048,
)
```

### Supported Models

Popular Ollama models for Islamic knowledge applications:

- `llama2` — Meta's Llama 2 (7B, 13B, 70B variants)
- `mistral` — Mistral 7B
- `phi` — Microsoft Phi-2 (2.7B, efficient for resource-constrained environments)
- `gemma` — Google Gemma (2B, 7B)
- `qwen` — Alibaba Qwen models
- `aya` — Cohere Aya (multilingual, supports Thai and Arabic)

### Starting Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Run Ollama server
ollama serve
```

Ollama listens on `http://localhost:11434` by default. The adapter automatically
appends `/v1` to match the OpenAI-compatible endpoint.

### No API Key Required

Ollama runs locally and does not require API keys. The adapter sets `api_key=None`.

## vLLM Adapter

vLLM is a high-throughput LLM serving system optimized for inference performance.
It supports continuous batching, paged attention, and multiple models.

### Configuration

```python
from zayd_service_orchestrator import VLLMLLMAdapter

adapter = VLLMLLMAdapter(
    provider_name="vllm",
    base_url="http://localhost:8000/v1",
    api_key=None,  # Optional, only if vLLM server requires it
    model_id="meta-llama/Llama-2-7b-chat-hf",
    timeout_ms=60_000,
    max_retries=1,
    max_input_tokens=4_096,
    max_output_tokens=2_048,
)
```

### Starting vLLM

```bash
# Install vLLM
pip install vllm

# Start vLLM server with OpenAI-compatible API
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --host 0.0.0.0 \
    --port 8000
```

vLLM exposes OpenAI-compatible endpoints at `http://localhost:8000/v1`.

### Optional Authentication

vLLM supports optional API key authentication:

```bash
# Start vLLM with API key
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --api-key vllm-secret-key
```

Then configure the adapter with the API key:

```python
adapter = VLLMLLMAdapter(
    api_key="vllm-secret-key",
    model_id="meta-llama/Llama-2-7b-chat-hf",
)
```

## Self-Host Profile

For minimal self-hosted deployment without cloud dependencies:

```python
from zayd_service_orchestrator import (
    AllowListedProviderRegistry,
    OllamaLLMAdapter,
)

registry = AllowListedProviderRegistry()

# Register local Ollama provider
registry.register(
    OllamaLLMAdapter(model_id="llama2"),
    enabled=True,
)

# Use in orchestration
provider = registry.load("llm", "ollama")
```

## Fallback Configuration

For production resilience, configure cloud LLM fallback:

```python
# Primary: local Ollama
primary = OllamaLLMAdapter(model_id="llama2")

# Fallback: OpenAI-compatible cloud provider
from zayd_service_orchestrator import OpenAICompatibleLLMAdapter
fallback = OpenAICompatibleLLMAdapter(
    provider_name="openai",
    base_url="https://api.openai.com/v1",
    api_key="sk-...",
    model_id="gpt-3.5-turbo",
)

registry.register(primary, enabled=True)
registry.register(fallback, enabled=True)

# Orchestrator tries primary first, falls back on unavailable health status
```

## Health Checks

Both adapters support health checks:

```python
health = await adapter.health_check()
# health.status: "ok" | "degraded" | "unavailable"
```

Health checks return `unavailable` when the local server is not reachable,
allowing orchestration to fall back to cloud providers.

## Performance Considerations

Local LLM adapters use longer default timeouts (60 seconds vs 30 seconds for
cloud providers) because local inference may be slower depending on hardware.

Adjust timeout based on your hardware:

```python
# Fast GPU: shorter timeout
adapter = OllamaLLMAdapter(timeout_ms=30_000)

# CPU-only: longer timeout
adapter = OllamaLLMAdapter(timeout_ms=120_000)
```

## Model Selection for Thai Islamic Content

Recommended models for Thai Islamic knowledge:

1. **Multilingual models**: `aya`, `qwen` (better Thai support)
2. **General-purpose**: `llama2`, `mistral` (good reasoning, less Thai fluency)
3. **Resource-efficient**: `phi` (2.7B, runs on modest hardware)

Test model quality with your specific content before production deployment.
