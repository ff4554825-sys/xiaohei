from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger

from ..types import Task, Event, EventType


class ContextGatherer:
    def __init__(self, memory_os=None, event_bus=None):
        self._memory_os = memory_os
        self._event_bus = event_bus
        logger.info("ContextGatherer initialized")

    def gather(self, task: Task) -> Dict[str, Any]:
        context: Dict[str, Any] = {}

        if self._memory_os:
            context["task_history"] = self._get_task_history(task)
            context["user_profile"] = self._get_user_profile(task)
            context["system_info"] = self._get_system_info()
            context["recent_tasks"] = self._get_recent_tasks()

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Context gathered for task: {task.id}",
                        "keys": list(context.keys()),
                    },
                    source="context_gatherer",
                )
            )

        logger.debug(f"Context gathered for task {task.id}: {len(context)} items")
        return context

    def _get_task_history(self, task: Task) -> List[Dict[str, Any]]:
        if not self._memory_os:
            return []

        results = self._memory_os.search(task.input, None)
        return [{"key": r["key"], "value": r["value"]} for r in results[:5]]

    def _get_user_profile(self, task: Task) -> Dict[str, Any]:
        if not self._memory_os:
            return {}

        user_id = task.context.get("user_id", "default")
        profile = self._memory_os.read("semantic", f"user_profile_{user_id}")

        if profile:
            return profile
        return {}

    def _get_system_info(self) -> Dict[str, Any]:
        import platform
        import os

        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cwd": os.getcwd(),
        }

    def _get_recent_tasks(self) -> List[Dict[str, Any]]:
        if not self._memory_os:
            return []

        results = self._memory_os.search("task_", None)
        return [{"key": r["key"], "value": r["value"]} for r in results[:10]]

    def inject_context(self, task: Task, context: Dict[str, Any]) -> Task:
        task.context.update(context)
        return task
