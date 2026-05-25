from typing import Dict, Any, List
from uuid import UUID
import asyncio
from loguru import logger

from ..types import Task, ExecutionResult, Event, EventType
from ..cognition import AgentRuntime, ToolRegistry, ContextEngine
from ..execution import MCPBus


class HermesMode:
    def __init__(self, tool_registry: ToolRegistry, context_engine: ContextEngine, event_bus):
        self._tool_registry = tool_registry
        self._context_engine = context_engine
        self._event_bus = event_bus
        self._agent_runtime = AgentRuntime(
            tool_registry=tool_registry,
            context_engine=context_engine,
            event_bus=event_bus,
        )
        self._mcp_bus = MCPBus(event_bus)
        logger.info("HermesMode initialized")

    async def run(self, task: Task) -> ExecutionResult:
        self._event_bus.publish(
            Event(
                type=EventType.TASK_START,
                payload={"task_id": str(task.id), "mode": "hermes"},
                source="hermes_mode",
            )
        )

        logger.info(f"HermesMode starting task: {task.id}")

        try:
            result = await self._agent_runtime.run(task)

            self._event_bus.publish(
                Event(
                    type=EventType.TASK_END,
                    payload={
                        "task_id": str(task.id),
                        "success": result.success,
                    },
                    source="hermes_mode",
                )
            )

            logger.info(f"HermesMode completed task: {task.id}")
            return result
        except Exception as e:
            logger.error(f"HermesMode error: {e}")

            self._event_bus.publish(
                Event(
                    type=EventType.ERROR,
                    payload={"task_id": str(task.id), "error": str(e)},
                    source="hermes_mode",
                )
            )

            return ExecutionResult(
                success=False,
                output=None,
                error=str(e),
                trace_id=task.id,
            )

    def register_tool(self, name: str, handler) -> None:
        self._tool_registry.register(name, "", handler)
        logger.info(f"Tool registered in HermesMode: {name}")

    def set_context(self, task_id: UUID, context: Dict[str, Any]) -> None:
        self._context_engine.store_context(task_id, context)
        logger.debug(f"Context set for task: {task_id}")
