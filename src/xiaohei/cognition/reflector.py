from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger

from ..types import Reflection, Task


class Reflector:
    def __init__(self):
        logger.info("Reflector initialized")

    def analyze(self, task: Task, execution_history: List[Dict[str, Any]]) -> Reflection:
        failures = [h for h in execution_history if not h.get("success", False)]

        if not failures:
            return Reflection(
                task_id=task.id,
                analysis="所有执行均成功，无需反思",
                root_cause="无失败",
                suggestions=[],
            )

        analysis = self._analyze_failures(failures)
        root_cause = self._identify_root_cause(failures)
        suggestions = self._generate_suggestions(root_cause, execution_history)

        reflection = Reflection(
            task_id=task.id,
            analysis=analysis,
            root_cause=root_cause,
            suggestions=suggestions,
        )

        logger.info(f"Reflection analysis completed for task: {task.id}")
        return reflection

    def _analyze_failures(self, failures: List[Dict[str, Any]]) -> str:
        error_counts: Dict[str, int] = {}

        for failure in failures:
            error = str(failure.get("error", "unknown"))
            error_type = self._classify_error(error)
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        analysis_parts = []
        for error_type, count in error_counts.items():
            analysis_parts.append(f"{error_type}: {count}次")

        return "; ".join(analysis_parts)

    def _classify_error(self, error: str) -> str:
        error_lower = error.lower()

        if "timeout" in error_lower:
            return "超时错误"
        if "network" in error_lower or "connection" in error_lower:
            return "网络错误"
        if "permission" in error_lower or "access denied" in error_lower:
            return "权限错误"
        if "syntax" in error_lower:
            return "语法错误"
        if "rate limit" in error_lower:
            return "限流错误"
        if "invalid" in error_lower:
            return "无效输入"
        if "not found" in error_lower:
            return "资源未找到"

        return "未知错误"

    def _identify_root_cause(self, failures: List[Dict[str, Any]]) -> str:
        first_failure = failures[0]
        error = str(first_failure.get("error", ""))
        context = first_failure.get("context", {})

        if "timeout" in error.lower():
            if context.get("execution_time", 0) > 30:
                return "执行时间过长导致超时"
            return "外部服务响应慢"

        if "network" in error.lower():
            return "网络连接不稳定"

        if "permission" in error.lower():
            return "缺少必要的权限"

        if "syntax" in error.lower():
            return "生成的代码存在语法问题"

        if len(failures) > 2:
            return "多次尝试均失败，可能是方案设计问题"

        return "单点故障"

    def _generate_suggestions(self, root_cause: str, history: List[Dict[str, Any]]) -> List[str]:
        suggestions = []

        if "超时" in root_cause:
            suggestions.append("考虑优化执行逻辑，减少计算量")
            suggestions.append("增加超时时间配置")
            suggestions.append("考虑并行化处理")

        if "网络" in root_cause:
            suggestions.append("检查网络连接")
            suggestions.append("考虑使用备用服务")
            suggestions.append("增加重试机制")

        if "权限" in root_cause:
            suggestions.append("检查API密钥配置")
            suggestions.append("确认权限范围")

        if "语法" in root_cause:
            suggestions.append("增加代码验证步骤")
            suggestions.append("使用代码格式化工具")

        if "方案设计" in root_cause:
            suggestions.append("重新评估任务分解方案")
            suggestions.append("考虑替代方案")

        if len(history) > 3:
            suggestions.append("考虑人工介入")

        return suggestions
