from typing import List, Dict, Any, Optional, List
from uuid import UUID
import asyncio
from loguru import logger

from ..types import Task, AgentPhase, Decision, DecisionType, ExecutionResult, Event, EventType
from ..control import FSMEngine, EventBus, Governance, PolicyController, BudgetManager
from ..cognition import TaskParser, Planner, FailureClassifier, Critic, ControlDecider, Reflector
from ..execution import Executor
from ..data import CheckpointOS


class XiaoHeiMode:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._fsm = FSMEngine()
        self._task_parser = TaskParser(event_bus)
        self._planner = Planner(event_bus)
        self._executor = Executor(event_bus=event_bus)
        self._critic = Critic(event_bus)
        self._control_decider = ControlDecider()
        self._reflector = Reflector()
        self._failure_classifier = FailureClassifier()
        self._checkpoint_os = CheckpointOS(event_bus=event_bus)
        self._governance = Governance(event_bus)
        self._policy_controller = PolicyController(event_bus)
        self._budget_manager = BudgetManager(event_bus)
        self._execution_history: Dict[UUID, List[Dict[str, Any]]] = {}

        self._fsm.on_transition(AgentPhase.PARSE_TASK, self._on_parse_task)
        self._fsm.on_transition(AgentPhase.DIVERGE, self._on_diverge)
        self._fsm.on_transition(AgentPhase.SCORER, self._on_scorer)
        self._fsm.on_transition(AgentPhase.DECOMPOSE, self._on_decompose)
        self._fsm.on_transition(AgentPhase.EXECUTE, self._on_execute)
        self._fsm.on_transition(AgentPhase.VERIFY, self._on_verify)
        self._fsm.on_transition(AgentPhase.CRITIC, self._on_critic)
        self._fsm.on_transition(AgentPhase.REFLECT, self._on_reflect)

        logger.info("XiaoHeiMode initialized")

    async def run(self, task: Task) -> ExecutionResult:
        self._execution_history[task.id] = []
        self._fsm.reset()

        self._event_bus.publish(
            Event(
                type=EventType.TASK_START,
                payload={"task_id": str(task.id), "input": task.input},
                source="xiaohei_mode",
            )
        )

        self._fsm.transition(AgentPhase.PARSE_TASK, self._event_bus)

        try:
            await self._process_task(task)

            final_result = self._get_final_result(task)

            self._event_bus.publish(
                Event(
                    type=EventType.TASK_END,
                    payload={
                        "task_id": str(task.id),
                        "success": final_result.success,
                    },
                    source="xiaohei_mode",
                )
            )

            return final_result
        except Exception as e:
            logger.error(f"XiaoHeiMode error: {e}")
            return ExecutionResult(
                success=False,
                output=None,
                error=str(e),
                trace_id=task.id,
            )

    async def _process_task(self, task: Task):
        while self._fsm.get_current_phase() not in [AgentPhase.FINISH, AgentPhase.ERROR]:
            await asyncio.sleep(0.1)

    def _on_parse_task(self, phase: AgentPhase):
        logger.debug("Transitioned to PARSE_TASK")

    def _on_diverge(self, phase: AgentPhase):
        logger.debug("Transitioned to DIVERGE")

    def _on_scorer(self, phase: AgentPhase):
        logger.debug("Transitioned to SCORER")

    def _on_decompose(self, phase: AgentPhase):
        logger.debug("Transitioned to DECOMPOSE")

    def _on_execute(self, phase: AgentPhase):
        logger.debug("Transitioned to EXECUTE")

    def _on_verify(self, phase: AgentPhase):
        logger.debug("Transitioned to VERIFY")

    def _on_critic(self, phase: AgentPhase):
        logger.debug("Transitioned to CRITIC")

    def _on_reflect(self, phase: AgentPhase):
        logger.debug("Transitioned to REFLECT")

    def _get_final_result(self, task: Task) -> ExecutionResult:
        history = self._execution_history.get(task.id, [])
        if history:
            last_result = history[-1]
            return ExecutionResult(
                success=last_result.get("success", False),
                output=last_result.get("output"),
                error=last_result.get("error"),
                trace_id=task.id,
            )
        return ExecutionResult(
            success=True,
            output="Task completed",
            trace_id=task.id,
        )

    def execute_step(self, task: Task, decision: Decision):
        if decision.type == DecisionType.RETRY:
            self._fsm.transition(AgentPhase.RETRY, self._event_bus)
            self._fsm.transition(AgentPhase.EXECUTE, self._event_bus)
        elif decision.type == DecisionType.REFLECT:
            self._fsm.transition(AgentPhase.REFLECT, self._event_bus)
        elif decision.type == DecisionType.FALLBACK:
            self._fsm.transition(AgentPhase.DIVERGE, self._event_bus)
        elif decision.type == DecisionType.FINISH:
            self._fsm.transition(AgentPhase.FINISH, self._event_bus)
        elif decision.type == DecisionType.HANDOFF:
            self._fsm.transition(AgentPhase.ERROR, self._event_bus)
