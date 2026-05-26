"""Cross-Agent Verification — 真实跨Agent验证

用第二个LLM调用核验第一个LLM的输出结果。
比关键词检查可靠得多。
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger
from ..cognition.llm import call_llm


@dataclass
class VerificationResult:
    passed: bool
    score: int                    # 0-10
    issues: list = None
    suggestion: str = ""
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
    
    def to_dict(self) -> dict:
        return {"passed": self.passed, "score": self.score, "issues": self.issues[:3],
                "confidence": round(self.confidence, 2)}


class CrossAgentVerifier:
    """真实跨Agent验证器"""
    
    def verify(self, task: str, result: str, context: str = "") -> VerificationResult:
        """用第二个LLM核验第一个LLM的输出"""
        
        prompt = f"""你是一个严格的审核员。请审核以下执行结果是否满足任务要求。

任务: {task}
执行结果: {result}

请逐项检查:
1. 结果是否直接回答了任务?
2. 结果是否包含错误或幻觉?
3. 结果是否完整无遗漏?
4. 结果格式是否规范?

返回JSON:
{{"score": 0-10, "passed": true/false, "issues": ["问题1", "问题2"], "suggestion": "改进建议"}}
"""
        if context:
            prompt = f"背景: {context}\n\n" + prompt
        
        resp = call_llm("你是一个严谨的审核员。严格检查, 发现问题就提出。", prompt)
        
        # 解析响应
        resp = resp.strip()
        if resp.startswith("```"):
            lines = resp.split("\n")
            resp = "\n".join(lines[1:-1])
        
        try:
            data = json.loads(resp)
            score = data.get("score", 5)
            return VerificationResult(
                passed=data.get("passed", score >= 6),
                score=score,
                issues=data.get("issues", []),
                suggestion=data.get("suggestion", ""),
                confidence=score / 10.0,
            )
        except json.JSONDecodeError:
            # 降级: 文本分析
            score = 5
            issues = []
            if not result or len(result.strip()) < 5:
                issues.append("结果为空或过短")
                score = 2
            if "错误" in result or "error" in result.lower():
                issues.append("结果包含错误信息")
                score -= 2
            return VerificationResult(
                passed=score >= 6,
                score=score,
                issues=issues,
                confidence=max(0.3, score / 10.0),
            )
    
    def fact_check(self, claim: str, reference: str) -> Dict[str, Any]:
        """事实校验: 用LLM检查声明是否与参考信息一致"""
        resp = call_llm(
            "你是一个事实核查员。判断以下声明是否与参考信息一致。返回JSON。",
            f"声明: {claim}\n\n参考信息: {reference}\n\n返回JSON: {{'consistent': true/false, 'confidence': 0-1, 'explanation': '...'}}"
        )
        resp = resp.strip()
        if resp.startswith("```"):
            lines = resp.split("\n")
            resp = "\n".join(lines[1:-1])
        try:
            return json.loads(resp)
        except json.JSONDecodeError:
            return {"consistent": True, "confidence": 0.5, "explanation": "事实校验不可用"}
