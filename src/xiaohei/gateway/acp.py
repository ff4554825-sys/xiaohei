from typing import Dict, Any, Optional
from loguru import logger
from jsonrpcserver import method, serve, Success, Error

from ..types import Task, TaskType
from ..cognition import TaskParser, Planner, Critic, ControlDecider


class ACPHandler:
    def __init__(self, task_parser=None, planner=None, critic=None, control_decider=None):
        self._task_parser = task_parser or TaskParser()
        self._planner = planner or Planner()
        self._critic = critic or Critic()
        self._control_decider = control_decider or ControlDecider()
        logger.info("ACP Handler initialized")

    @method
    def parse_task(request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            input_text = request.get("input", "")
            if not input_text:
                return Error(code=-32602, message="Missing input")

            task = self._task_parser.parse(input_text)
            return Success({
                "task_id": str(task.id),
                "type": task.type.value,
                "risk": task.risk.level,
                "complexity": task.complexity.score,
            })
        except Exception as e:
            return Error(code=-32603, message=str(e))

    @method
    def plan_task(task_id: str, input_text: str) -> Dict[str, Any]:
        try:
            task = Task(
                id=task_id,
                type=TaskType.INFORMATION,
                input=input_text,
            )

            plans = self._planner.diverge(task)
            scored_plans = self._planner.score(plans, task)
            selected_plan = self._planner.select(scored_plans)

            return Success({
                "plans_count": len(plans),
                "selected_score": selected_plan.total_score if selected_plan else 0,
                "steps": selected_plan.plan if selected_plan else [],
            })
        except Exception as e:
            return Error(code=-32603, message=str(e))

    @method
    def review_result(task_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            task = Task(
                id=task_id,
                type=TaskType.INFORMATION,
                input="",
            )

            review = self._critic.review(task, result)
            decision = self._control_decider.decide(task, review)

            return Success({
                "review": review,
                "decision": {
                    "type": decision.type.value,
                    "reason": decision.reason,
                },
            })
        except Exception as e:
            return Error(code=-32603, message=str(e))

    @method
    def health() -> Dict[str, Any]:
        return Success({"status": "healthy", "version": "1.0.0"})

    def start(self, host: str = "localhost", port: int = 5000) -> None:
        logger.info(f"ACP Handler starting on {host}:{port}")
        serve(host, port)
