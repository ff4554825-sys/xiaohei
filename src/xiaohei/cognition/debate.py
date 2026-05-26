"""Multi-Agent Debate — 真实多Agent辩论

每个 Agent 使用不同的角色系统提示词 + 真实 LLM 调用。
4个角色独立发表意见 → 交叉投票 → 输出共识。
"""

import json
from typing import List, Dict, Any
from dataclasses import dataclass, field
from loguru import logger
from .llm import call_llm


ROLES = {
    "planner": {
        "name": "规划者",
        "system": "你是一个谨慎的规划者。你擅长制定详细、可执行的步骤计划。关注: 可行性、资源需求、风险。",
    },
    "critic": {
        "name": "评论者",
        "system": "你是一个尖锐的评论者。你专门找方案中的漏洞和问题。关注: 逻辑漏洞、遗漏场景、过度假设。",
    },
    "researcher": {
        "name": "研究员",
        "system": "你是一个客观的研究员。你提供事实和参考信息。关注: 数据支撑、已知方法、历史经验。",
    },
    "executor": {
        "name": "执行者",
        "system": "你是一个务实的执行者。你评估方案的实际可操作性。关注: 执行难度、时间成本、依赖条件。",
    },
}


@dataclass
class Opinion:
    role: str
    content: str
    confidence: float = 0.5
    votes_for: int = 0
    votes_against: int = 0
    
    def to_dict(self) -> dict:
        return {"role": self.role, "opinion": self.content[:100], 
                "confidence": self.confidence, "votes_for": self.votes_for, "votes_against": self.votes_against}


@dataclass
class DebateResult:
    topic: str
    opinions: List[Opinion] = field(default_factory=list)
    consensus: str = ""
    consensus_confidence: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "topic": self.topic[:50],
            "opinions": [o.to_dict() for o in self.opinions],
            "consensus": self.consensus[:100],
            "consensus_confidence": round(self.consensus_confidence, 2),
        }


class Debate:
    """真实多Agent辩论"""
    
    def debate(self, topic: str, context: str = "") -> DebateResult:
        result = DebateResult(topic=topic)
        
        # 第一轮: 各角色独立发表意见
        for role_id, role_info in ROLES.items():
            content = call_llm(
                role_info["system"],
                f"议题: {topic}\n\n背景信息: {context}\n\n请以{role_info['name']}的身份发表对这个议题的意见和建议。"
            )
            opinion = Opinion(role=role_id, content=content, confidence=0.7)
            result.opinions.append(opinion)
            logger.info(f"[debate] {role_id} 已发表意见")
        
        # 第二轮: 互评 + 投票
        for i, opinion in enumerate(result.opinions):
            others = [o for j, o in enumerate(result.opinions) if j != i]
            others_text = "\n\n".join([f"[{o.role}] {o.content[:200]}" for o in others])
            
            vote = call_llm(
                f"你是{ROLES[opinion.role]['name']}。请阅读其他角色的观点, 然后投票: 支持(+)或反对(-)或中立(0)。只返回一个字符: + - 0",
                f"你的观点: {opinion.content[:200]}\n\n其他人的观点:\n{others_text}"
            )
            vote = vote.strip()
            if "+" in vote:
                opinion.votes_for += 1
            elif "-" in vote:
                opinion.votes_against += 1
        
        # 计算共识: 收集所有意见, LLM 综合判断
        all_opinions = "\n\n".join([f"[{o.role}] (支持{ o.votes_for }/反对{ o.votes_against }) {o.content[:200]}" for o in result.opinions])
        
        consensus = call_llm(
            "你是辩论主持人。综合各方观点, 给出最终的共识结论。",
            f"议题: {topic}\n\n各方观点:\n{all_opinions}\n\n请总结共识结论:"
        )
        result.consensus = consensus
        
        # 共识置信度: 基于投票
        total_votes = sum(o.votes_for + o.votes_against for o in result.opinions)
        total_for = sum(o.votes_for for o in result.opinions)
        result.consensus_confidence = total_for / max(total_votes, 1)
        
        return result
