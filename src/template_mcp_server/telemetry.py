from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

_initialized = False
_enabled = False
_tracer_name = "template-mcp-server"

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except Exception:  # pragma: no cover - graceful fallback when deps are unavailable
    trace = None  # type: ignore[assignment]
    OTLPMetricExporter = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment]
    MeterProvider = None  # type: ignore[assignment]
    PeriodicExportingMetricReader = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]
    BatchSpanProcessor = None  # type: ignore[assignment]
    SERVICE_NAME = "service.name"  # type: ignore[assignment]
    SERVICE_VERSION = "service.version"  # type: ignore[assignment]


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def setup_telemetry(service_name: str, service_version: str, logger: logging.Logger) -> bool:
    global _initialized, _enabled, _tracer_name

    if _initialized:
        return _enabled

    _enabled = _env_bool("OTEL_ENABLED", False) or _env_bool("ENABLE_TRACING", False)
    _tracer_name = service_name.strip() or "template-mcp-server"
    if not _enabled:
        _initialized = True
        return False

    if not all([trace, TracerProvider, BatchSpanProcessor, OTLPSpanExporter, Resource]):
        logger.warning("OpenTelemetry requested but dependencies are unavailable")
        _initialized = True
        _enabled = False
        return False

    resource = Resource.create(
        {
            SERVICE_NAME: _tracer_name,
            SERVICE_VERSION: service_version.strip() or "0.1.0",
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    if MeterProvider and PeriodicExportingMetricReader and OTLPMetricExporter:
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    exporter=OTLPMetricExporter(),
                    export_interval_millis=15000,
                )
            ],
        )
        from opentelemetry import metrics

        metrics.set_meter_provider(meter_provider)

    logger.info("OpenTelemetry initialized", extra={"otel_enabled": True, "service_name": _tracer_name})
    _initialized = True
    return True


@contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    if not _enabled or trace is None:
        yield
        return
    tracer = trace.get_tracer(_tracer_name)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                if value is None:
                    continue
                span.set_attribute(key, value)
        yield


def current_trace_ids() -> tuple[str | None, str | None]:
    if not _enabled or trace is None:
        return None, None
    span = trace.get_current_span()
    if span is None:
        return None, None
    span_context = span.get_span_context()
    if not span_context or not span_context.trace_id or not span_context.span_id:
        return None, None
    return f"{span_context.trace_id:032x}", f"{span_context.span_id:016x}"
