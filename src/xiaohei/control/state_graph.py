"""State Graph — 混合核心(FSM + State Graph)

在 FSM 的刚性状态迁移基础上, 叠加 State Graph 的灵活流转能力。
- FSM: 刚性边界(安全红线)
- State Graph: 柔性流转(复杂多分支)
- Time-Travel Checkpoint: 任意状态回退
"""

from typing import Dict, Set, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from ..types import AgentPhase


@dataclass
class GraphNode:
    """状态图节点"""
    phase: AgentPhase
    description: str = ""
    handlers: Dict[str, Callable] = field(default_factory=dict)
    
    def add_handler(self, event: str, handler: Callable):
        self.handlers[event] = handler


@dataclass
class TimeTravelPoint:
    """时间旅行检查点"""
    phase: AgentPhase
    timestamp: float = 0.0
    snapshot: dict = field(default_factory=dict)
    memo: str = ""


class StateGraph:
    """状态图 — 在FSM之上增加柔性流转
    
    FSM: 决定"能不能过去"
    State Graph: 决定"怎么过去最好"
    """
    
    def __init__(self):
        self._nodes: Dict[AgentPhase, GraphNode] = {}
        self._edges: Dict[AgentPhase, Set[AgentPhase]] = {}
        self._checkpoints: List[TimeTravelPoint] = []
        self._current: Optional[AgentPhase] = None
        self._history: List[TimeTravelPoint] = []
    
    def add_node(self, phase: AgentPhase, description: str = ""):
        self._nodes[phase] = GraphNode(phase=phase, description=description)
        if phase not in self._edges:
            self._edges[phase] = set()
    
    def add_edge(self, from_phase: AgentPhase, to_phase: AgentPhase):
        if from_phase not in self._edges:
            self._edges[from_phase] = set()
        self._edges[from_phase].add(to_phase)
    
    def transition(self, to: AgentPhase, context: dict = None) -> bool:
        """状态迁移(安全检查 + 灵活路径)"""
        if self._current is None:
            self._current = to
            self._save_checkpoint(f"初始: {to.value}")
            return True
        
        # FSM 硬检查
        from ..control.fsm import PHASE_TRANSITIONS
        allowed = PHASE_TRANSITIONS.get(self._current, set())
        
        if to in allowed:
            self._save_checkpoint(f"{self._current.value} → {to.value}")
            self._current = to
            return True
        
        # State Graph 柔性检查(允许预设的额外路径)
        if self._current in self._edges and to in self._edges[self._current]:
            logger.info(f"[state_graph] 柔性迁移: {self._current.value} → {to.value}")
            self._save_checkpoint(f"柔性: {self._current.value} → {to.value}")
            self._current = to
            return True
        
        logger.warning(f"[state_graph] 非法迁移: {self._current.value} → {to.value}")
        return False
    
    def time_travel(self, target_phase: AgentPhase) -> bool:
        """时间旅行: 回退到指定状态"""
        for i, cp in enumerate(self._checkpoints):
            if cp.phase == target_phase:
                self._current = cp.phase
                logger.info(f"[state_graph] ⏪ 时间旅行到: {target_phase.value} (检查点#{i})")
                # 裁剪该点之后的检查点
                self._checkpoints = self._checkpoints[:i + 1]
                return True
        logger.warning(f"[state_graph] 无法回退: {target_phase.value} 不在检查点中")
        return False
    
    def _save_checkpoint(self, memo: str = ""):
        cp = TimeTravelPoint(
            phase=self._current,
            timestamp=__import__('time').time(),
            snapshot={"current": self._current.value if self._current else None},
            memo=memo,
        )
        self._checkpoints.append(cp)
        self._history.append(cp)
    
    @property
    def checkpoints(self) -> List[dict]:
        return [{"phase": c.phase.value, "memo": c.memo} for c in self._checkpoints[-10:]]
    
    @property
    def current(self) -> Optional[AgentPhase]:
        return self._current
