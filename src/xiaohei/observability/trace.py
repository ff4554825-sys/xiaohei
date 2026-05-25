from typing import List, Dict, List, Any, Optional
from uuid import UUID, uuid4
from loguru import logger
from datetime import datetime

from ..types import Span, Event, EventType


class TraceManager:
    def __init__(self, event_bus=None):
        self._spans: Dict[UUID, Span] = {}
        self._active_spans: Dict[str, UUID] = {}
        self._event_bus = event_bus
        logger.info("TraceManager initialized")

    def start_span(self, name: str, parent_id: Optional[UUID] = None) -> UUID:
        span = Span(
            name=name,
            parent_id=parent_id,
        )
        self._spans[span.id] = span

        if parent_id:
            self._active_spans[f"{parent_id}-{name}"] = span.id
        else:
            self._active_spans[name] = span.id

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={"message": f"Span started: {name}", "span_id": str(span.id)},
                    source="trace",
                )
            )

        logger.debug(f"Span started: {name} ({span.id})")
        return span.id

    def end_span(self, span_id: UUID) -> Optional[Span]:
        span = self._spans.get(span_id)
        if not span:
            logger.warning(f"Span not found: {span_id}")
            return None

        span.end_time = datetime.now()
        span.duration = (span.end_time - span.start_time).total_seconds()

        keys_to_remove = [k for k, v in self._active_spans.items() if v == span_id]
        for key in keys_to_remove:
            del self._active_spans[key]

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Span ended: {span.name}",
                        "span_id": str(span.id),
                        "duration": span.duration,
                    },
                    source="trace",
                )
            )

        logger.debug(f"Span ended: {span.name} ({span.id}) - {span.duration:.2f}s")
        return span

    def record_event(self, span_id: UUID, name: str, attributes: Dict[str, Any] = {}) -> None:
        span = self._spans.get(span_id)
        if span:
            span.events.append({
                "name": name,
                "attributes": attributes,
                "timestamp": datetime.now().isoformat(),
            })
            logger.debug(f"Event recorded in span {span_id}: {name}")

    def set_attribute(self, span_id: UUID, key: str, value: Any) -> None:
        span = self._spans.get(span_id)
        if span:
            span.attributes[key] = value

    def get_span(self, span_id: UUID) -> Optional[Span]:
        return self._spans.get(span_id)

    def get_spans_by_parent(self, parent_id: UUID) -> List[Span]:
        return [s for s in self._spans.values() if s.parent_id == parent_id]

    def get_trace_tree(self, root_span_id: UUID) -> Dict[str, Any]:
        root = self._spans.get(root_span_id)
        if not root:
            return {}

        return self._build_tree(root)

    def _build_tree(self, span: Span) -> Dict[str, Any]:
        children = self.get_spans_by_parent(span.id)
        children_tree = [self._build_tree(child) for child in children]

        return {
            "id": str(span.id),
            "name": span.name,
            "duration": span.duration,
            "attributes": span.attributes,
            "children": children_tree,
        }

    def calculate_percentiles(self, span_ids: List[UUID]) -> Dict[str, float]:
        durations = []
        for span_id in span_ids:
            span = self._spans.get(span_id)
            if span and span.duration:
                durations.append(span.duration)

        if not durations:
            return {}

        durations.sort()
        n = len(durations)

        return {
            "p50": durations[int(n * 0.5)] if n > 0 else 0,
            "p95": durations[int(n * 0.95)] if n > 0 else 0,
            "p99": durations[int(n * 0.99)] if n > 0 else 0,
            "avg": sum(durations) / n if n > 0 else 0,
        }

    def clear(self) -> None:
        self._spans.clear()
        self._active_spans.clear()
        logger.info("TraceManager cleared")
