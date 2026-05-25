from typing import List, Dict, List, Any, Optional, Callable
from uuid import UUID
import asyncio
from loguru import logger

from ..types import Task, ExecutionResult, Event, EventType


class Executor:
    def __init__(self, tool_registry=None, event_bus=None):
        self._tool_registry = tool_registry
        self._event_bus = event_bus
        logger.info("Executor initialized")

    async def execute(self, task: Task, steps: List[Dict[str, Any]]) -> ExecutionResult:
        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Starting execution for task: {task.id}",
                        "steps": len(steps),
                    },
                    source="executor",
                )
            )

        logger.info(f"Executing task: {task.id} with {len(steps)} steps")

        results = []
        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i+1}")
            tool_name = step.get("tool")
            args = step.get("args", {})

            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.TOOL_CALL,
                        payload={
                            "step": i + 1,
                            "name": step_name,
                            "tool": tool_name,
                        },
                        source="executor",
                    )
                )

            try:
                result = await self._execute_step(tool_name, args, task)
                results.append({
                    "step": i + 1,
                    "name": step_name,
                    "success": True,
                    "output": result,
                })

                if self._event_bus:
                    self._event_bus.publish(
                        Event(
                            type=EventType.TOOL_RESULT,
                            payload={
                                "step": i + 1,
                                "name": step_name,
                                "success": True,
                            },
                            source="executor",
                        )
                    )

            except Exception as e:
                error_msg = str(e)
                results.append({
                    "step": i + 1,
                    "name": step_name,
                    "success": False,
                    "error": error_msg,
                })

                if self._event_bus:
                    self._event_bus.publish(
                        Event(
                            type=EventType.ERROR,
                            payload={
                                "step": i + 1,
                                "name": step_name,
                                "error": error_msg,
                            },
                            source="executor",
                        )
                    )

                logger.error(f"Step {i+1} failed: {error_msg}")

                return ExecutionResult(
                    success=False,
                    output=None,
                    error=error_msg,
                    trace_id=task.id,
                )

        final_output = self._aggregate_results(results)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Execution completed for task: {task.id}",
                        "success": True,
                    },
                    source="executor",
                )
            )

        logger.info(f"Execution completed for task: {task.id}")
        return ExecutionResult(
            success=True,
            output=final_output,
            trace_id=task.id,
        )

    async def _execute_step(self, tool_name: Optional[str], args: Dict[str, Any], task: Task) -> Any:
        if not tool_name:
            return {"message": "No tool specified"}

        if self._tool_registry:
            skill = self._tool_registry.find(tool_name)
            if skill:
                handler = self._get_handler(skill.handler)
                if handler:
                    return await self._invoke_handler(handler, args)
                else:
                    raise Exception(f"Handler not found for tool: {tool_name}")
            else:
                raise Exception(f"Tool not found: {tool_name}")

        raise Exception(f"No tool registry available")

    def _get_handler(self, handler_name: str) -> Optional[Callable]:
        return None

    async def _invoke_handler(self, handler: Callable, args: Dict[str, Any]) -> Any:
        if asyncio.iscoroutinefunction(handler):
            return await handler(**args)
        return handler(**args)

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Any:
        if len(results) == 1:
            return results[0].get("output")

        aggregated = {}
        for result in results:
            aggregated[result["name"]] = result.get("output")

        return aggregated

    def decompose(self, task: Task) -> List[Dict[str, Any]]:
        steps = []

        if task.type.value == "creation":
            steps = [
                {"name": "分析需求", "tool": "analyze_task"},
                {"name": "生成内容", "tool": "generate_content"},
                {"name": "验证输出", "tool": "validate_output"},
            ]
        elif task.type.value == "analysis":
            steps = [
                {"name": "收集信息", "tool": "gather_info"},
                {"name": "分析数据", "tool": "analyze_data"},
                {"name": "生成报告", "tool": "generate_report"},
            ]
        elif task.type.value == "action":
            steps = [
                {"name": "验证权限", "tool": "verify_permission"},
                {"name": "执行操作", "tool": "execute_action"},
                {"name": "确认结果", "tool": "confirm_result"},
            ]
        else:
            steps = [
                {"name": "处理任务", "tool": "process_task"},
            ]

        logger.debug(f"Task decomposed into {len(steps)} steps")
        return steps
