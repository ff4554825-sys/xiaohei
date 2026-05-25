from typing import Dict, Any, Optional
from loguru import logger

from ..types import Task, TaskType, TaskConstraint, TaskRisk, TaskComplexity, Event, EventType


class TaskParser:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        logger.info("TaskParser initialized")

    def parse(self, input_text: str) -> Task:
        task_type = self.classify(input_text)
        constraints = self._extract_constraints(input_text)
        risk = self._analyze_risk(input_text)
        complexity = self._calculate_complexity(input_text)

        task = Task(
            type=task_type,
            input=input_text,
            constraints=constraints,
            risk=risk,
            complexity=complexity,
        )

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Task parsed: {task_type.value}",
                        "task_id": str(task.id),
                    },
                    source="task_parser",
                )
            )

        logger.info(f"Task parsed: {task.id} - {task_type.value}")
        return task

    def classify(self, input_text: str) -> TaskType:
        input_lower = input_text.lower()

        if any(keyword in input_lower for keyword in ["写", "创建", "生成", "制作", "构建"]):
            return TaskType.CREATION
        elif any(keyword in input_lower for keyword in ["分析", "评估", "审查", "检查"]):
            return TaskType.ANALYSIS
        elif any(keyword in input_lower for keyword in ["转换", "转换为", "格式", "导出"]):
            return TaskType.TRANSFORMATION
        elif any(keyword in input_lower for keyword in ["执行", "运行", "调用", "操作"]):
            return TaskType.ACTION
        elif any(keyword in input_lower for keyword in ["研究", "调研", "搜索", "查找"]):
            return TaskType.RESEARCH
        elif any(keyword in input_lower for keyword in ["教", "解释", "学习", "说明"]):
            return TaskType.EDUCATION
        elif any(keyword in input_lower for keyword in ["调试", "修复", "错误", "bug"]):
            return TaskType.DEBUG

        return TaskType.INFORMATION

    def _extract_constraints(self, input_text: str) -> TaskConstraint:
        constraints = TaskConstraint()

        if "快速" in input_text or "尽快" in input_text:
            constraints.max_time = 300

        if "简短" in input_text or "简洁" in input_text:
            constraints.max_tokens = 500

        return constraints

    def _analyze_risk(self, input_text: str) -> TaskRisk:
        risk = TaskRisk()
        input_lower = input_text.lower()

        dangerous_keywords = ["删除", "修改", "覆盖", "危险", "风险"]
        sensitive_keywords = ["密码", "密钥", "token", "api key"]

        if any(keyword in input_lower for keyword in dangerous_keywords):
            risk.level = "high"
            risk.categories.append("destructive")

        if any(keyword in input_lower for keyword in sensitive_keywords):
            risk.level = "high"
            risk.categories.append("sensitive")

        if risk.level == "high":
            risk.mitigation = "需要用户确认后执行"

        return risk

    def _calculate_complexity(self, input_text: str) -> TaskComplexity:
        complexity = TaskComplexity()

        length_score = min(len(input_text) / 1000, 1.0)
        sentence_count = input_text.count("。") + input_text.count("?") + input_text.count("!")
        sentence_score = min(sentence_count / 10, 1.0)

        complexity.score = (length_score + sentence_score) / 2
        complexity.factors = {
            "length": length_score,
            "sentences": sentence_score,
        }

        return complexity
