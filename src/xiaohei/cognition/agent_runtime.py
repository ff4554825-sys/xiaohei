from typing import List, Dict, List, Any, Optional, Callable
from uuid import UUID
import asyncio
from loguru import logger

from ..types import Task, ToolCall, ToolResult, ExecutionResult, Event, EventType


class AgentRuntime:
    def __init__(self, tool_registry=None, context_engine=None, event_bus=None):
        self._tool_registry = tool_registry
        self._context_engine = context_engine
        self._event_bus = event_bus
        self._running = False
        logger.info("AgentRuntime initialized")

    async def run(self, task: Task) -> ExecutionResult:
        self._running = True
        logger.info(f"Starting AgentRuntime for task: {task.id}")

        try:
            context = {}
            if self._context_engine:
                context = self._context_engine.gather_context(task.id, ["task_history", "user_preferences"])

            loop_count = 0
            max_loops = 10
            execution_history = []

            while self._running and loop_count < max_loops:
                loop_count += 1
                logger.debug(f"Tool loop iteration: {loop_count}")

                llm_response = await self._call_llm(task, context, execution_history)
                tool_call = self._parse_tool_call(llm_response)

                if tool_call:
                    result = await self._execute_tool(tool_call)
                    execution_history.append({
                        "tool_call": tool_call.dict(),
                        "result": result.dict(),
                    })

                    if result.success:
                        context["last_tool_result"] = result.output
                    else:
                        context["last_error"] = result.error

                    if self._context_engine:
                        self._context_engine.store_context(task.id, context)
                else:
                    break

            final_result = self._summarize(task, execution_history)

            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.LOG,
                        payload={
                            "message": f"AgentRuntime completed task: {task.id}",
                            "success": final_result.success,
                        },
                        source="agent_runtime",
                    )
                )

            return final_result

        except Exception as e:
            logger.error(f"AgentRuntime error: {e}")
            return ExecutionResult(
                success=False,
                output=None,
                error=str(e),
                trace_id=task.id,
            )

    async def _call_llm(self, task: Task, context: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        """真实 LLM 调用"""
        from .llm import call_llm
        
        system = f"你是{self._config.name or '小黑'}, 一个智能助手。\\n任务类型: {task.type.value}\\n背景: {context}"
        user = task.input
        
        # 加入历史
        for h in history[-5:]:
            user += f"\\n{h.get('role', 'user')}: {h.get('content', '')}"
        
        return call_llm(system, user)

    def _parse_tool_call(self, llm_response: str) -> Optional[ToolCall]:
        return None

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        if self._tool_registry:
            skill = self._tool_registry.find(tool_call.tool_name)
            if skill:
                try:
                    handler = self._get_handler(skill.handler)
                    if handler:
                        result = await self._invoke_handler(handler, tool_call.args)
                        return ToolResult(
                            tool_call_id=tool_call.id,
                            success=True,
                            output=result,
                        )
                except Exception as e:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        success=False,
                        error=str(e),
                    )

        return ToolResult(
            tool_call_id=tool_call.id,
            success=False,
            error="Tool not found",
        )

    def _get_handler(self, handler_name: str) -> Optional[Callable]:
        return None

    async def _invoke_handler(self, handler: Callable, args: Dict[str, Any]) -> Any:
        if asyncio.iscoroutinefunction(handler):
            return await handler(**args)
        return handler(**args)

    def _summarize(self, task: Task, execution_history: List[Dict[str, Any]]) -> ExecutionResult:
        successes = sum(1 for h in execution_history if h["result"].get("success", False))
        total = len(execution_history)

        if total == 0:
            return ExecutionResult(
                success=True,
                output="Task completed without tool calls",
                trace_id=task.id,
            )

        if successes == total:
            return ExecutionResult(
                success=True,
                output=f"All {total} tool calls succeeded",
                trace_id=task.id,
            )

        return ExecutionResult(
            success=False,
            output=f"{successes}/{total} tool calls succeeded",
            error=f"{total - successes} tool calls failed",
            trace_id=task.id,
        )

    def stop(self) -> None:
        self._running = False
        logger.info("AgentRuntime stopped")
