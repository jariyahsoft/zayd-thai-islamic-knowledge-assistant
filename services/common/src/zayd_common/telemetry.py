from __future__ import annotations

import os
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class SpanRecord:
    name: str
    started_at: datetime
    ended_at: datetime
    duration_ms: float
    attributes: dict[str, object]


@dataclass(frozen=True)
class CounterSnapshot:
    name: str
    value: float
    labels: dict[str, str]


@dataclass(frozen=True)
class HistogramSnapshot:
    name: str
    count: int
    sum_value: float
    labels: dict[str, str]


@dataclass
class MetricCounter:
    name: str
    description: str
    label_names: tuple[str, ...]
    values: dict[tuple[str, ...], float] = field(default_factory=dict)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = _metric_key(self.label_names, labels)
        self.values[key] = self.values.get(key, 0.0) + amount

    def snapshot(self) -> list[CounterSnapshot]:
        return [
            CounterSnapshot(
                name=self.name,
                value=value,
                labels=dict(zip(self.label_names, key, strict=True)),
            )
            for key, value in sorted(self.values.items())
        ]


@dataclass
class MetricHistogram:
    name: str
    description: str
    label_names: tuple[str, ...]
    sums: dict[tuple[str, ...], float] = field(default_factory=dict)
    counts: dict[tuple[str, ...], int] = field(default_factory=dict)

    def observe(self, value: float, **labels: str) -> None:
        key = _metric_key(self.label_names, labels)
        self.sums[key] = self.sums.get(key, 0.0) + value
        self.counts[key] = self.counts.get(key, 0) + 1

    def snapshot(self) -> list[HistogramSnapshot]:
        return [
            HistogramSnapshot(
                name=self.name,
                count=self.counts[key],
                sum_value=self.sums[key],
                labels=dict(zip(self.label_names, key, strict=True)),
            )
            for key in sorted(self.counts)
        ]


class TelemetryRegistry:
    def __init__(self, *, sample_rate: float | None = None) -> None:
        self._lock = Lock()
        self._spans: deque[SpanRecord] = deque(maxlen=512)
        self._counters: dict[str, MetricCounter] = {}
        self._histograms: dict[str, MetricHistogram] = {}
        self._sample_rate = _normalize_sample_rate(
            sample_rate if sample_rate is not None else os.getenv("TELEMETRY_SAMPLE_RATE")
        )

    def counter(
        self,
        name: str,
        description: str,
        *,
        label_names: tuple[str, ...] = (),
    ) -> MetricCounter:
        with self._lock:
            counter = self._counters.get(name)
            if counter is None:
                counter = MetricCounter(name=name, description=description, label_names=label_names)
                self._counters[name] = counter
            return counter

    def histogram(
        self,
        name: str,
        description: str,
        *,
        label_names: tuple[str, ...] = (),
    ) -> MetricHistogram:
        with self._lock:
            histogram = self._histograms.get(name)
            if histogram is None:
                histogram = MetricHistogram(
                    name=name,
                    description=description,
                    label_names=label_names,
                )
                self._histograms[name] = histogram
            return histogram

    @contextmanager
    def span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
    ) -> Iterator[dict[str, object]]:
        started = datetime.now(UTC)
        started_perf = perf_counter()
        mutable_attributes = sanitize_attributes(attributes or {})
        sampled = self._should_sample(name, mutable_attributes)
        try:
            yield mutable_attributes
        finally:
            if sampled:
                ended = datetime.now(UTC)
                record = SpanRecord(
                    name=name,
                    started_at=started,
                    ended_at=ended,
                    duration_ms=(perf_counter() - started_perf) * 1000,
                    attributes=mutable_attributes,
                )
                with self._lock:
                    self._spans.append(record)

    def record_counter(self, name: str, amount: float = 1.0, **labels: str) -> None:
        self.counter(
            name,
            description=name,
            label_names=tuple(sorted(labels)),
        ).inc(amount, **labels)

    def record_histogram(self, name: str, value: float, **labels: str) -> None:
        self.histogram(
            name,
            description=name,
            label_names=tuple(sorted(labels)),
        ).observe(value, **labels)

    def spans(self) -> tuple[SpanRecord, ...]:
        with self._lock:
            return tuple(self._spans)

    def counters(self) -> tuple[CounterSnapshot, ...]:
        with self._lock:
            counters = list(self._counters.values())
        snapshots: list[CounterSnapshot] = []
        for counter in counters:
            snapshots.extend(counter.snapshot())
        return tuple(snapshots)

    def histograms(self) -> tuple[HistogramSnapshot, ...]:
        with self._lock:
            histograms = list(self._histograms.values())
        snapshots: list[HistogramSnapshot] = []
        for histogram in histograms:
            snapshots.extend(histogram.snapshot())
        return tuple(snapshots)

    def reset(self) -> None:
        with self._lock:
            self._spans.clear()
            self._counters.clear()
            self._histograms.clear()

    def set_sample_rate(self, sample_rate: float | str) -> None:
        with self._lock:
            self._sample_rate = _normalize_sample_rate(sample_rate)

    def sample_rate(self) -> float:
        with self._lock:
            return self._sample_rate

    def export_prometheus_text(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = list(self._counters.values())
            histograms = list(self._histograms.values())
        for counter in counters:
            lines.append(f"# HELP {counter.name} {counter.description}")
            lines.append(f"# TYPE {counter.name} counter")
            counter_snapshots: list[CounterSnapshot] = counter.snapshot()
            for counter_snapshot in counter_snapshots:
                lines.append(
                    _metric_line(
                        counter_snapshot.name,
                        counter_snapshot.value,
                        counter_snapshot.labels,
                    )
                )
        for histogram in histograms:
            lines.append(f"# HELP {histogram.name} {histogram.description}")
            lines.append(f"# TYPE {histogram.name}_sum gauge")
            lines.append(f"# TYPE {histogram.name}_count gauge")
            histogram_snapshots: list[HistogramSnapshot] = histogram.snapshot()
            for histogram_snapshot in histogram_snapshots:
                lines.append(
                    _metric_line(
                        f"{histogram_snapshot.name}_sum",
                        histogram_snapshot.sum_value,
                        histogram_snapshot.labels,
                    )
                )
                lines.append(
                    _metric_line(
                        f"{histogram_snapshot.name}_count",
                        histogram_snapshot.count,
                        histogram_snapshot.labels,
                    )
                )
        return "\n".join(lines) + ("\n" if lines else "")

    def _should_sample(self, name: str, attributes: dict[str, object]) -> bool:
        with self._lock:
            sample_rate = self._sample_rate
        if sample_rate <= 0.0:
            return False
        if sample_rate >= 1.0:
            return True
        basis = (
            attributes.get("trace_id")
            or attributes.get("request_id")
            or attributes.get("stream_id")
            or name
        )
        digest = sha256(str(basis).encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
        return bucket <= sample_rate


def _metric_key(label_names: tuple[str, ...], labels: dict[str, str]) -> tuple[str, ...]:
    return tuple(labels.get(name, "") for name in label_names)


def _metric_line(name: str, value: float | int, labels: dict[str, str]) -> str:
    if not labels:
        return f"{name} {value}"
    label_blob = ",".join(
        f'{key}="{_escape_label(label_value)}"'
        for key, label_value in sorted(labels.items())
    )
    return f"{name}{{{label_blob}}} {value}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_sample_rate(value: float | str | None) -> float:
    if value is None:
        return 1.0
    parsed = float(value)
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError("telemetry sample rate must be between 0.0 and 1.0")
    return parsed


def sanitize_attributes(attributes: dict[str, object]) -> dict[str, object]:
    blocked_fragments = ("prompt", "message", "secret", "token", "document_text", "answer_text")
    return {
        key: value
        for key, value in attributes.items()
        if not any(fragment in key.lower() for fragment in blocked_fragments)
    }


telemetry_registry = TelemetryRegistry()


def instrumented(
    name: str,
    *,
    attribute_builder: Callable[..., dict[str, object]] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def build_attributes(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, object]:
            if attribute_builder is None:
                return {}
            return sanitize_attributes(attribute_builder(*args, **kwargs))

        if callable(func) and callable(getattr(func, "__await__", None)):
            raise TypeError("Use instrumented_async for coroutine functions")

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with telemetry_registry.span(name, attributes=build_attributes(args, kwargs)):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def instrumented_async(
    name: str,
    *,
    attribute_builder: Callable[..., dict[str, object]] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attributes = (
                sanitize_attributes(attribute_builder(*args, **kwargs))
                if attribute_builder
                else {}
            )
            with telemetry_registry.span(name, attributes=attributes):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "CounterSnapshot",
    "HistogramSnapshot",
    "MetricCounter",
    "MetricHistogram",
    "SpanRecord",
    "TelemetryRegistry",
    "instrumented",
    "instrumented_async",
    "sanitize_attributes",
    "telemetry_registry",
]
