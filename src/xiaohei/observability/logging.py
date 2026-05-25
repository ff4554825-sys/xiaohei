from typing import Dict, Any
from loguru import logger as loguru_logger
import sys

from ..types import Event, EventType


class LoggingManager:
    def __init__(self, level: str = "INFO", event_bus=None):
        self._event_bus = event_bus
        self._configure_logger(level)
        logger.info("LoggingManager initialized")

    def _configure_logger(self, level: str):
        loguru_logger.remove()

        loguru_logger.add(
            sys.stdout,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )

        loguru_logger.add(
            "./logs/xiaohei_{time:YYYY-MM-DD}.log",
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="7 days",
            compression="zip",
        )

    def trace(self, message: str, **kwargs) -> None:
        loguru_logger.trace(message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        loguru_logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        loguru_logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        loguru_logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        loguru_logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        loguru_logger.critical(message, **kwargs)

    def log_event(self, event: Event) -> None:
        if event.type == EventType.ERROR:
            self.error(f"Event: {event.type.value} - {event.payload}")
        elif event.type == EventType.WARNING:
            self.warning(f"Event: {event.type.value} - {event.payload}")
        else:
            self.info(f"Event: {event.type.value} - {event.payload}")

    def log_metric(self, metric: Dict[str, Any]) -> None:
        self.info(f"Metric: {metric['name']} = {metric['value']}")

    def set_level(self, level: str) -> None:
        loguru_logger.remove()
        self._configure_logger(level)
        self.info(f"Log level changed to: {level}")
