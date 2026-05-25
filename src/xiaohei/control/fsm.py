from typing import Dict, Set, Optional, Callable, Any
from enum import Enum
from loguru import logger

from ..types import AgentPhase, Event, EventType


PHASE_TRANSITIONS: Dict[AgentPhase, Set[AgentPhase]] = {
    AgentPhase.IDLE: {
        AgentPhase.PARSE_TASK,
    },
    AgentPhase.PARSE_TASK: {
        AgentPhase.DIVERGE,
        AgentPhase.ERROR,
    },
    AgentPhase.DIVERGE: {
        AgentPhase.SEARCH,
        AgentPhase.SCORER,
        AgentPhase.DECOMPOSE,
        AgentPhase.ERROR,
    },
    AgentPhase.SEARCH: {
        AgentPhase.SCORER,
        AgentPhase.DECOMPOSE,
        AgentPhase.ERROR,
    },
    AgentPhase.SCORER: {
        AgentPhase.DECOMPOSE,
        AgentPhase.DIVERGE,
        AgentPhase.ERROR,
    },
    AgentPhase.DECOMPOSE: {
        AgentPhase.EXECUTE,
        AgentPhase.ERROR,
    },
    AgentPhase.EXECUTE: {
        AgentPhase.VERIFY,
        AgentPhase.RETRY,
        AgentPhase.ERROR,
    },
    AgentPhase.VERIFY: {
        AgentPhase.CRITIC,
        AgentPhase.RETRY,
        AgentPhase.FINISH,
        AgentPhase.ERROR,
    },
    AgentPhase.CRITIC: {
        AgentPhase.REFLECT,
        AgentPhase.RETRY,
        AgentPhase.FINISH,
        AgentPhase.HANDOFF,
    },
    AgentPhase.REFLECT: {
        AgentPhase.EXECUTE,
        AgentPhase.DIVERGE,
        AgentPhase.FINISH,
        AgentPhase.ERROR,
    },
    AgentPhase.RETRY: {
        AgentPhase.EXECUTE,
        AgentPhase.ERROR,
    },
    AgentPhase.FINISH: {
        AgentPhase.IDLE,
    },
    AgentPhase.ERROR: {
        AgentPhase.IDLE,
        AgentPhase.RETRY,
        AgentPhase.REFLECT,
    },
}


class FSMEngine:
    def __init__(self):
        self.current_phase: AgentPhase = AgentPhase.IDLE
        self._transition_callbacks: Dict[AgentPhase, Set[Callable[[AgentPhase], Any]]] = {}
        logger.info(f"FSM Engine initialized, current phase: {self.current_phase}")

    def validate_transition(self, target_phase: AgentPhase) -> bool:
        valid_transitions = PHASE_TRANSITIONS.get(self.current_phase, set())
        is_valid = target_phase in valid_transitions
        if not is_valid:
            logger.warning(f"Invalid transition from {self.current_phase} to {target_phase}")
        return is_valid

    def transition(self, target_phase: AgentPhase, event_bus=None) -> bool:
        if not self.validate_transition(target_phase):
            if event_bus:
                event_bus.publish(
                    Event(
                        type=EventType.ERROR,
                        payload={
                            "message": f"Invalid phase transition: {self.current_phase} -> {target_phase}"
                        },
                        source="fsm",
                    )
                )
            return False

        previous_phase = self.current_phase
        self.current_phase = target_phase

        if event_bus:
            event_bus.publish(
                Event(
                    type=EventType.PHASE_CHANGE,
                    payload={
                        "from": previous_phase.value,
                        "to": target_phase.value,
                    },
                    source="fsm",
                )
            )

        logger.info(f"Phase transition: {previous_phase} -> {target_phase}")

        for callback in self._transition_callbacks.get(target_phase, set()):
            try:
                callback(target_phase)
            except Exception as e:
                logger.error(f"Transition callback error: {e}")

        return True

    def on_transition(self, phase: AgentPhase, callback: Callable[[AgentPhase], Any]) -> None:
        if phase not in self._transition_callbacks:
            self._transition_callbacks[phase] = set()
        self._transition_callbacks[phase].add(callback)
        logger.debug(f"Added transition callback for phase: {phase}")

    def get_current_phase(self) -> AgentPhase:
        return self.current_phase

    def reset(self) -> None:
        self.current_phase = AgentPhase.IDLE
        logger.info("FSM Engine reset to IDLE")
