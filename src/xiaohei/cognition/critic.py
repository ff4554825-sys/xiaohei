from typing import List, Dict, Any, Optional
from loguru import logger

from ..types import Task, Reflection, Event, EventType


class Critic:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        logger.info("Critic initialized")

    def review(self, task: Task, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        review = {
            "success": execution_result.get("success", False),
            "alignment": self._check_alignment(task, execution_result),
            "correctness": self._check_correctness(execution_result),
            "completeness": self._check_completeness(task, execution_result),
            "safety": self._check_safety(execution_result),
            "suggestions": [],
        }

        if not review["success"]:
            review["suggestions"].append("执行失败，需要重试或调整")

        if review["alignment"] < 0.7:
            review["suggestions"].append("输出与任务目标不够对齐")

        if review["correctness"] < 0.7:
            review["suggestions"].append("输出可能存在错误")

        if review["completeness"] < 0.8:
            review["suggestions"].append("输出不够完整")

        if review["safety"] < 0.9:
            review["suggestions"].append("检测到潜在安全问题")

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": "Critic review completed",
                        "task_id": str(task.id),
                        "review": review,
                    },
                    source="critic",
                )
            )

        logger.info(f"Critic review completed for task: {task.id}")
        return review

    def _check_alignment(self, task: Task, result: Dict[str, Any]) -> float:
        output = str(result.get("output", ""))
        input_text = task.input

        keywords_input = set(input_text.lower().split()[:10])
        keywords_output = set(output.lower().split()[:10])

        if not keywords_input:
            return 1.0

        overlap = len(keywords_input.intersection(keywords_output))
        return min(1.0, overlap / len(keywords_input))

    def _check_correctness(self, result: Dict[str, Any]) -> float:
        output = str(result.get("output", ""))

        error_indicators = ["error", "failed", "exception", "invalid", "wrong"]
        success_indicators = ["success", "completed", "done", "正确", "完成"]

        error_count = sum(1 for indicator in error_indicators if indicator in output.lower())
        success_count = sum(1 for indicator in success_indicators if indicator in output.lower())

        if error_count > 0:
            return max(0.0, 0.5 - error_count * 0.1)
        if success_count > 0:
            return min(1.0, 0.7 + success_count * 0.1)

        return 0.7

    def _check_completeness(self, task: Task, result: Dict[str, Any]) -> float:
        output = str(result.get("output", ""))

        if len(output) < 10:
            return 0.3
        if len(output) < 50:
            return 0.5
        if len(output) < 200:
            return 0.7

        return 0.9

    def _check_safety(self, result: Dict[str, Any]) -> float:
        output = str(result.get("output", ""))

        dangerous_patterns = [
            "rm -rf",
            "delete all",
            "drop table",
            "format disk",
            "password",
            "secret",
            "api key",
        ]

        for pattern in dangerous_patterns:
            if pattern.lower() in output.lower():
                logger.warning(f"Safety check failed: {pattern} detected")
                return 0.5

        return 1.0

    def analyze(self, task: Task, execution_history: List[Dict[str, Any]]) -> Reflection:
        reflections = []

        for attempt in execution_history:
            if not attempt.get("success", False):
                error = attempt.get("error", "")
                if error:
                    reflections.append(f"尝试失败: {error}")

        analysis = "\n".join(reflections) if reflections else "执行过程正常"

        reflection = Reflection(
            task_id=task.id,
            analysis=analysis,
            root_cause=self._determine_root_cause(execution_history),
            suggestions=self._generate_suggestions(execution_history),
        )

        logger.info(f"Reflection generated for task: {task.id}")
        return reflection

    def _determine_root_cause(self, history: List[Dict[str, Any]]) -> str:
        failures = [h for h in history if not h.get("success", False)]

        if not failures:
            return "未知"

        error_types = []
        for failure in failures:
            error = str(failure.get("error", ""))
            if "timeout" in error.lower():
                error_types.append("超时")
            elif "permission" in error.lower():
                error_types.append("权限")
            elif "network" in error.lower():
                error_types.append("网络")
            elif "syntax" in error.lower():
                error_types.append("语法")

        if error_types:
            return ", ".join(set(error_types))

        return "其他"

    def _generate_suggestions(self, history: List[Dict[str, Any]]) -> List[str]:
        suggestions = []

        timeout_count = sum(1 for h in history if "timeout" in str(h.get("error", "")).lower())
        if timeout_count > 1:
            suggestions.append("考虑增加超时时间或优化执行效率")

        permission_count = sum(1 for h in history if "permission" in str(h.get("error", "")).lower())
        if permission_count > 0:
            suggestions.append("检查权限配置")

        return suggestions
