from typing import Dict, Set, Callable, Any, Optional, Pattern
import re
from loguru import logger

from ..types import Event, EventType


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable[[Event], Any]]] = {}
        self._wildcard_subscribers: Set[Callable[[Event], Any]] = set()
        logger.info("EventBus initialized")

    def _match_topic(self, event_type: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", event_type))

    def subscribe(self, topic: str, callback: Callable[[Event], Any]) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(callback)
        logger.debug(f"Subscriber added for topic: {topic}")

    def subscribe_wildcard(self, callback: Callable[[Event], Any]) -> None:
        self._wildcard_subscribers.add(callback)
        logger.debug("Wildcard subscriber added")

    def unsubscribe(self, topic: str, callback: Callable[[Event], Any]) -> bool:
        if topic in self._subscribers and callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)
            logger.debug(f"Subscriber removed from topic: {topic}")
            return True
        return False

    def unsubscribe_wildcard(self, callback: Callable[[Event], Any]) -> bool:
        if callback in self._wildcard_subscribers:
            self._wildcard_subscribers.remove(callback)
            logger.debug("Wildcard subscriber removed")
            return True
        return False

    def publish(self, event: Event) -> None:
        event_type = event.type.value if isinstance(event.type, EventType) else str(event.type)
        logger.debug(f"Publishing event: {event_type}")

        matched = False

        for topic, callbacks in self._subscribers.items():
            if self._match_topic(event_type, topic):
                for callback in callbacks:
                    try:
                        callback(event)
                        matched = True
                    except Exception as e:
                        logger.error(f"Error processing event callback for topic {topic}: {e}")

        for callback in self._wildcard_subscribers:
            try:
                callback(event)
                matched = True
            except Exception as e:
                logger.error(f"Error processing wildcard callback: {e}")

        if not matched:
            logger.debug(f"No subscribers for event: {event_type}")
