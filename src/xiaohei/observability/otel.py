from typing import Dict, Any, Optional
from loguru import logger

from ..types import Span


class OpenTelemetryExporter:
    def __init__(self, endpoint: Optional[str] = None):
        self._endpoint = endpoint
        self._tracer = None
        self._meter = None
        self._initialized = False
        self._init_otel()
        logger.info("OpenTelemetryExporter initialized")

    def _init_otel(self):
        try:
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

            trace.set_tracer_provider(TracerProvider())
            metrics.set_meter_provider(MeterProvider())

            self._tracer = trace.get_tracer("xiaohei")
            self._meter = metrics.get_meter("xiaohei")

            if self._endpoint:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

                trace.get_tracer_provider().add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=self._endpoint))
                )

                metric_reader = PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=self._endpoint)
                )
                metrics.get_meter_provider().add_metric_reader(metric_reader)

            self._initialized = True
            logger.info("OpenTelemetry initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")

    def export_span(self, span: Span) -> None:
        if not self._initialized or not self._tracer:
            return

        with self._tracer.start_as_current_span(span.name) as otel_span:
            otel_span.set_attributes(span.attributes)
            for event in span.events:
                otel_span.add_event(event.get("name", ""), event.get("attributes", {}))

    def record_metric(self, name: str, value: float, labels: Dict[str, str] = {}) -> None:
        if not self._initialized or not self._meter:
            return

        counter = self._meter.create_counter(name)
        counter.add(value, labels)

    def is_initialized(self) -> bool:
        return self._initialized
