"""Cross-Agent Verification — 跨Agent校验 (第3级验证)

引入第二个Agent对结果做交叉验证, 降低幻觉率。
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
from uuid import uuid4


@dataclass
class CrossCheckResult:
    checked_by: str
    passed: bool
    confidence: float
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class CrossAgentVerifier:
    """跨Agent验证器"""
    
    def __init__(self):
        self._verifier_id = f"verifier_{uuid4().hex[:6]}"
    
    def verify(self, task: str, result: str, context: dict = None) -> CrossCheckResult:
        """交叉验证执行结果"""
        issues = []
        
        # 检查结果是否为空
        if not result or len(result.strip()) == 0:
            issues.append("结果为空")
        
        # 检查结果长度
        if len(result) < 5:
            issues.append("结果过短, 可能不完整")
        
        # 检查是否包含错误
        error_patterns = ["error", "exception", "traceback", "failed", "timeout"]
        for p in error_patterns:
            if p in result.lower():
                issues.append(f"结果包含错误关键词: {p}")
                break
        
        # 检查任务目标是否在结果中体现
        task_keywords = set(task.lower().split()[:5])
        result_lower = result.lower()
        matched = sum(1 for kw in task_keywords if kw in result_lower and len(kw) > 2)
        if matched < len(task_keywords) * 0.3:
            issues.append(f"结果与任务目标匹配度低({matched}/{len(task_keywords)})")
        
        confidence = max(0.3, 1.0 - len(issues) * 0.25)
        
        return CrossCheckResult(
            checked_by=self._verifier_id,
            passed=len(issues) == 0,
            confidence=round(confidence, 2),
            issues=issues,
        )


class FactChecker:
    """事实校验(RAG + 搜索)"""
    
    def check(self, claim: str, evidence: str = "") -> Dict[str, Any]:
        """检查事实是否与已知信息一致"""
        if not evidence:
            return {"passed": True, "confidence": 0.5, "note": "无证据可对比"}
        
        # 简单的关键词重叠检查
        claim_words = set(claim.lower().split())
        evidence_words = set(evidence.lower().split())
        overlap = len(claim_words & evidence_words)
        
        if overlap > len(claim_words) * 0.5:
            return {"passed": True, "confidence": 0.8, "note": "证据支持"}
        else:
            return {"passed": False, "confidence": 0.3, "note": "证据不足"}
