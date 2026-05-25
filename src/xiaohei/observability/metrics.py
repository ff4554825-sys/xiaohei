from typing import List, Dict, List, Any, Callable
from loguru import logger
from datetime import datetime
import time

from ..types import Metric, MetricType


class MetricsManager:
    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._metric_callbacks: List[Callable[[], Metric]] = []
        logger.info("MetricsManager initialized")

    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = {}) -> None:
        key = self._get_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value
        logger.debug(f"Counter incremented: {name} -> {self._counters[key]}")

    def decrement(self, name: str, value: float = 1.0, labels: Dict[str, str] = {}) -> None:
        key = self._get_key(name, labels)
        self._counters[key] = max(0, self._counters.get(key, 0) - value)
        logger.debug(f"Counter decremented: {name} -> {self._counters[key]}")

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = {}) -> None:
        key = self._get_key(name, labels)
        self._gauges[key] = value
        logger.debug(f"Gauge set: {name} -> {value}")

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = {}) -> None:
        key = self._get_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-500:]

        logger.debug(f"Histogram recorded: {name} -> {value}")

    def _get_key(self, name: str, labels: Dict[str, str]) -> str:
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}|{label_str}" if label_str else name

    def get_counter(self, name: str, labels: Dict[str, str] = {}) -> float:
        key = self._get_key(name, labels)
        return self._counters.get(key, 0)

    def get_gauge(self, name: str, labels: Dict[str, str] = {}) -> float:
        key = self._get_key(name, labels)
        return self._gauges.get(key, 0)

    def get_histogram_stats(self, name: str, labels: Dict[str, str] = {}) -> Dict[str, float]:
        key = self._get_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {}

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    def register_callback(self, callback: Callable[[], Metric]) -> None:
        self._metric_callbacks.append(callback)
        logger.info("Metric callback registered")

    def collect(self) -> List[Metric]:
        metrics = []

        for name, value in self._counters.items():
            metrics.append(Metric(
                name=name.split("|")[0],
                type=MetricType.COUNTER,
                value=value,
                labels=self._parse_labels(name),
            ))

        for name, value in self._gauges.items():
            metrics.append(Metric(
                name=name.split("|")[0],
                type=MetricType.GAUGE,
                value=value,
                labels=self._parse_labels(name),
            ))

        for name, values in self._histograms.items():
            if values:
                metrics.append(Metric(
                    name=name.split("|")[0],
                    type=MetricType.HISTOGRAM,
                    value=sum(values) / len(values),
                    labels=self._parse_labels(name),
                ))

        for callback in self._metric_callbacks:
            try:
                metric = callback()
                metrics.append(metric)
            except Exception as e:
                logger.error(f"Metric callback failed: {e}")

        return metrics

    def _parse_labels(self, key: str) -> Dict[str, str]:
        parts = key.split("|")
        if len(parts) < 2:
            return {}

        labels = {}
        for part in parts[1].split(","):
            k, v = part.split("=")
            labels[k] = v
        return labels

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        logger.info("MetricsManager reset")
