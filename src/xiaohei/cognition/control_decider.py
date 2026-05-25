from typing import Dict, Any
from loguru import logger

from ..types import Decision, DecisionType, Task


class ControlDecider:
    def __init__(self):
        logger.info("ControlDecider initialized")

    def decide(self, task: Task, review: Dict[str, Any]) -> Decision:
        if not review.get("success", False):
            error = review.get("error", "")

            if "syntax" in error.lower():
                return Decision(
                    type=DecisionType.RETRY,
                    reason="语法错误，直接重试",
                    params={"max_retries": 2},
                )

            if "幻觉" in error.lower() or "hallucination" in error.lower():
                return Decision(
                    type=DecisionType.REFLECT,
                    reason="检测到幻觉，需要反思",
                    params={},
                )

            if "timeout" in error.lower() or "服务不可用" in error.lower():
                return Decision(
                    type=DecisionType.FALLBACK,
                    reason="服务不可用，降级处理",
                    params={},
                )

            if "安全" in error.lower() or "permission" in error.lower():
                return Decision(
                    type=DecisionType.HANDOFF,
                    reason="安全拦截，需要人工介入",
                    params={},
                )

            return Decision(
                type=DecisionType.RETRY,
                reason="执行失败，重试",
                params={"max_retries": 3},
            )

        alignment = review.get("alignment", 0.0)
        correctness = review.get("correctness", 0.0)
        completeness = review.get("completeness", 0.0)

        if alignment < 0.5 or correctness < 0.5:
            return Decision(
                type=DecisionType.REFLECT,
                reason="输出质量不达标，需要反思优化",
                params={},
            )

        if completeness < 0.7:
            return Decision(
                type=DecisionType.RETRY,
                reason="输出不够完整，需要补充",
                params={"mode": "continue"},
            )

        return Decision(
            type=DecisionType.FINISH,
            reason="任务完成",
            params={},
        )

    def decide_from_history(self, task: Task, execution_history: list[Dict[str, Any]]) -> Decision:
        attempts = len(execution_history)
        failures = sum(1 for h in execution_history if not h.get("success", False))

        if attempts >= 5:
            return Decision(
                type=DecisionType.HANDOFF,
                reason=f"已尝试{attempts}次，均未成功，需要人工介入",
                params={},
            )

        if failures >= 3:
            return Decision(
                type=DecisionType.REFLECT,
                reason=f"失败{failures}次，需要分析原因",
                params={},
            )

        last_result = execution_history[-1] if execution_history else None
        if last_result:
            return self.decide(task, last_result)

        return Decision(
            type=DecisionType.FINISH,
            reason="无执行记录",
            params={},
        )
