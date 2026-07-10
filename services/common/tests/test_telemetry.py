from __future__ import annotations

import pytest
from zayd_common.telemetry import sanitize_attributes, telemetry_registry


def test_span_sanitizer_excludes_sensitive_fields() -> None:
    attributes = sanitize_attributes(
        {
            "trace_id": "trace-1",
            "prompt_body": "hidden",
            "message_text": "private",
            "provider_name": "openai",
        }
    )

    assert attributes == {"trace_id": "trace-1", "provider_name": "openai"}


def test_telemetry_registry_records_span_and_metrics() -> None:
    telemetry_registry.reset()
    with telemetry_registry.span("test.span", attributes={"trace_id": "trace-telemetry"}):
        telemetry_registry.record_counter("test_counter_total", service="api")
        telemetry_registry.record_histogram("test_latency_ms", 12.5, service="api")

    spans = telemetry_registry.spans()
    assert any(span.name == "test.span" for span in spans)

    text = telemetry_registry.export_prometheus_text()
    assert "test_counter_total" in text
    assert "test_latency_ms_sum" in text


def test_telemetry_sampling_is_configurable_and_deterministic() -> None:
    telemetry_registry.reset()
    telemetry_registry.set_sample_rate(0.0)
    with telemetry_registry.span("test.unsampled", attributes={"trace_id": "trace-a"}):
        pass

    assert not any(span.name == "test.unsampled" for span in telemetry_registry.spans())

    telemetry_registry.set_sample_rate(1.0)
    with telemetry_registry.span("test.sampled", attributes={"trace_id": "trace-b"}):
        pass

    assert any(span.name == "test.sampled" for span in telemetry_registry.spans())


def test_telemetry_invalid_sample_rate_is_rejected() -> None:
    with pytest.raises(ValueError):
        telemetry_registry.set_sample_rate(1.5)
