"""Multi-Agent Debate — 多Agent辩论与交叉验证

让多个Agent针对同一问题给出不同方案，交叉验证结果。
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger
from uuid import uuid4


@dataclass
class AgentOpinion:
    """单个Agent的意见"""
    agent_id: str
    role: str                    # planner / critic / researcher / executor
    opinion: str
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)
    votes_for: int = 0
    votes_against: int = 0


@dataclass
class DebateResult:
    """辩论结果"""
    topic: str
    opinions: List[AgentOpinion] = field(default_factory=list)
    consensus: Optional[str] = None
    consensus_score: float = 0.0
    rounds: int = 0
    
    @property
    def winner(self) -> Optional[AgentOpinion]:
        if not self.opinions:
            return None
        return max(self.opinions, key=lambda o: o.votes_for - o.votes_against)


class DebateModerator:
    """辩论主持人 — 管理多Agent辩论流程"""
    
    def __init__(self):
        self._roles = ["planner", "critic", "researcher", "executor"]
    
    def debate(self, topic: str, context: dict = None) -> DebateResult:
        """主持一场辩论"""
        result = DebateResult(topic=topic)
        
        # 第一轮: 各Agent独立发表意见
        for role in self._roles:
            opinion = self._generate_opinion(role, topic, context)
            result.opinions.append(opinion)
            logger.info(f"[debate] {role} 发表意见, 置信度={opinion.confidence}")
        
        # 第二轮: 互评
        for opinion in result.opinions:
            for other in result.opinions:
                if opinion.agent_id != other.agent_id:
                    vote = self._cross_vote(opinion, other)
                    if vote > 0:
                        opinion.votes_for += 1
                    else:
                        opinion.votes_against += 1
        
        result.rounds = 2
        
        # 共识: 得票最高的方案
        winner = result.winner
        if winner:
            result.consensus = winner.opinion
            result.consensus_score = winner.confidence * (1 + winner.votes_for - winner.votes_against)
        
        logger.info(f"[debate] 辩论结束, 共识={result.consensus_score:.2f}")
        return result
    
    def _generate_opinion(self, role: str, topic: str, context: dict) -> AgentOpinion:
        """生成Agent意见(基于规则, 实际应调LLM)"""
        opinions = {
            "planner": f"作为规划者: 建议分3步完成'{topic[:30]}'",
            "critic": f"作为评论者: 方案可行但需要注意执行顺序",
            "researcher": f"作为研究者: 已有类似方案可以参考",
            "executor": f"作为执行者: 可以在10步内完成",
        }
        return AgentOpinion(
            agent_id=str(uuid4())[:8],
            role=role,
            opinion=opinions.get(role, ""),
            confidence={"planner": 0.7, "critic": 0.8, "researcher": 0.6, "executor": 0.9}.get(role, 0.5),
        )
    
    def _cross_vote(self, a: AgentOpinion, b: AgentOpinion) -> int:
        """交叉投票: 1支持, -1反对, 0中立"""
        if a.role == "critic":
            return -1  # 评论者通常反对
        if a.role == b.role:
            return 0
        return 1 if b.confidence > 0.6 else -1
