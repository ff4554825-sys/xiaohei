from typing import List, Dict, List, Any, Optional
from loguru import logger

from ..types import FailureType, FailurePattern


class FailureClassifier:
    def __init__(self):
        self._patterns: List[FailurePattern] = self._load_patterns()
        logger.info("FailureClassifier initialized with {} patterns", len(self._patterns))

    def _load_patterns(self) -> List[FailurePattern]:
        return [
            FailurePattern(
                type=FailureType.SYNTAX_ERROR,
                pattern=r"syntax error|invalid syntax|parse error",
                recovery_strategy="retry_with_fix",
            ),
            FailurePattern(
                type=FailureType.SYNTAX_ERROR,
                pattern=r"unexpected token|missing.*parenthesis|missing.*bracket",
                recovery_strategy="retry_with_fix",
            ),
            FailurePattern(
                type=FailureType.SEMANTIC_ERROR,
                pattern=r"undefined.*variable|unknown.*function|not defined",
                recovery_strategy="reflect_and_adjust",
            ),
            FailurePattern(
                type=FailureType.SEMANTIC_ERROR,
                pattern=r"type error|type mismatch|invalid type",
                recovery_strategy="reflect_and_adjust",
            ),
            FailurePattern(
                type=FailureType.EXECUTION_ERROR,
                pattern=r"runtime error|exception|traceback",
                recovery_strategy="retry",
            ),
            FailurePattern(
                type=FailureType.EXECUTION_ERROR,
                pattern=r"connection refused|timeout|network error",
                recovery_strategy="fallback",
            ),
            FailurePattern(
                type=FailureType.TIMEOUT,
                pattern=r"timeout|time limit exceeded",
                recovery_strategy="retry_with_timeout",
            ),
            FailurePattern(
                type=FailureType.RATE_LIMITED,
                pattern=r"rate limit|too many requests",
                recovery_strategy="backoff_retry",
            ),
            FailurePattern(
                type=FailureType.PERMISSION_DENIED,
                pattern=r"permission denied|access denied|forbidden",
                recovery_strategy="handoff",
            ),
            FailurePattern(
                type=FailureType.UNKNOWN,
                pattern=r"error|failed|unexpected",
                recovery_strategy="reflect",
            ),
        ]

    def classify(self, error_message: str) -> List[FailurePattern]:
        matched = []
        error_lower = error_message.lower()

        for pattern in self._patterns:
            if self._match_pattern(pattern.pattern, error_lower):
                pattern.confidence = self._calculate_confidence(pattern.pattern, error_lower)
                matched.append(pattern)

        matched.sort(key=lambda p: p.confidence, reverse=True)

        if matched:
            logger.info(f"Classified failure: {matched[0].type.value} (confidence: {matched[0].confidence})")
        else:
            logger.warning(f"No failure pattern matched for: {error_message}")

        return matched

    def _match_pattern(self, pattern: str, text: str) -> bool:
        import re

        return bool(re.search(pattern, text))

    def _calculate_confidence(self, pattern: str, text: str) -> float:
        import re

        matches = re.findall(pattern, text)
        if matches:
            return min(1.0, 0.5 + len(matches) * 0.1)
        return 0.5

    def get_recovery_strategy(self, error_message: str) -> Optional[str]:
        patterns = self.classify(error_message)
        if patterns:
            return patterns[0].recovery_strategy
        return None
