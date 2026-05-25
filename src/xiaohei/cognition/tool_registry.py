from typing import List, Dict, List, Any, Optional, Callable
from uuid import UUID, uuid4
from loguru import logger

from ..types import Skill, Event, EventType


class ToolRegistry:
    def __init__(self, event_bus=None):
        self._tools: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}
        self._event_bus = event_bus
        logger.info("ToolRegistry initialized")

    def register(self, name: str, description: str, handler: Callable, schema: Dict[str, Any] = {}, category: str = "general") -> Skill:
        skill = Skill(
            name=name,
            description=description,
            schema=schema,
            handler=handler.__name__,
            category=category,
        )

        self._tools[name] = skill

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Tool registered: {name}",
                        "category": category,
                    },
                    source="tool_registry",
                )
            )

        logger.info(f"Tool registered: {name}")
        return skill

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            skill = self._tools.pop(name)

            if skill.category in self._categories:
                self._categories[skill.category].remove(name)

            logger.info(f"Tool unregistered: {name}")
            return True
        return False

    def find(self, name: str) -> Optional[Skill]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Skill]:
        if category:
            tool_names = self._categories.get(category, [])
            return [self._tools[name] for name in tool_names]
        return list(self._tools.values())

    def get_categories(self) -> List[str]:
        return list(self._categories.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool_count(self) -> int:
        return len(self._tools)
