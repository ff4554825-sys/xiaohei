from typing import Dict, Any, List
from loguru import logger

from ..types import Task, Event, EventType


class SemanticCheck:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        logger.info("SemanticCheck initialized")

    def check(self, task: Task, output: str) -> Dict[str, Any]:
        alignment = self._check_alignment(task, output)
        relevance = self._check_relevance(task, output)
        consistency = self._check_consistency(output)
        safety = self._check_safety(output)

        result = {
            "alignment": alignment,
            "relevance": relevance,
            "consistency": consistency,
            "safety": safety,
            "overall": (alignment + relevance + consistency + safety) / 4,
        }

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={"message": "Semantic check completed", "result": result},
                    source="semantic_check",
                )
            )

        return result

    def _check_alignment(self, task: Task, output: str) -> float:
        input_words = set(task.input.lower().split())
        output_words = set(output.lower().split())

        if not input_words:
            return 1.0

        overlap = len(input_words.intersection(output_words))
        return min(1.0, overlap / len(input_words))

    def _check_relevance(self, task: Task, output: str) -> float:
        task_type = task.type.value
        output_lower = output.lower()

        keywords = {
            "creation": ["create", "write", "generate", "build"],
            "analysis": ["analyze", "report", "find", "determine"],
            "action": ["execute", "run", "call", "perform"],
            "information": ["what", "how", "explain", "describe"],
        }

        expected_keywords = keywords.get(task_type, [])
        if not expected_keywords:
            return 0.7

        found_count = sum(1 for kw in expected_keywords if kw in output_lower)
        return min(1.0, found_count / len(expected_keywords))

    def _check_consistency(self, output: str) -> float:
        sentences = [s.strip() for s in output.split(".") if s.strip()]
        if len(sentences) < 2:
            return 1.0

        score = 0.0
        for i in range(len(sentences) - 1):
            sentence1 = sentences[i].lower()
            sentence2 = sentences[i + 1].lower()

            words1 = set(sentence1.split())
            words2 = set(sentence2.split())

            if words1 and words2:
                overlap = len(words1.intersection(words2))
                score += overlap / max(len(words1), len(words2))

        return score / (len(sentences) - 1)

    def _check_safety(self, output: str) -> float:
        dangerous_patterns = [
            "rm -rf",
            "delete all",
            "drop table",
            "format disk",
            ":(){ :|:& };:",
        ]

        for pattern in dangerous_patterns:
            if pattern.lower() in output.lower():
                logger.warning(f"Dangerous content detected: {pattern}")
                return 0.3

        return 1.0
