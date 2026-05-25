from typing import List, Dict, Any, List
from loguru import logger

from ..types import Event, EventType, PolicyRule, PolicyType


class PolicyCheck:
    def __init__(self, event_bus=None):
        self._rules: List[PolicyRule] = []
        self._event_bus = event_bus
        self._load_default_rules()
        logger.info("PolicyCheck initialized")

    def _load_default_rules(self):
        self._rules = [
            PolicyRule(
                name="no_dangerous_commands",
                type=PolicyType.BLACKLIST,
                description="Block dangerous shell commands",
                conditions={"patterns": ["rm -rf", "dd if=", "mkfs", ":(){ :|:& };:"]},
                action="block",
            ),
            PolicyRule(
                name="no_sensitive_data",
                type=PolicyType.BLACKLIST,
                description="Block sensitive data in output",
                conditions={"patterns": ["password", "secret", "api_key", "token"]},
                action="redact",
            ),
            PolicyRule(
                name="rate_limit",
                type=PolicyType.RATE_LIMIT,
                description="Limit tool calls per minute",
                conditions={"limit": 60},
                action="block",
            ),
        ]

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        logger.info(f"Policy rule added: {rule.name}")

    def check(self, content: str, context: Dict[str, Any] = {}) -> Dict[str, Any]:
        violations = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            if rule.type == PolicyType.BLACKLIST:
                patterns = rule.conditions.get("patterns", [])
                for pattern in patterns:
                    if pattern.lower() in content.lower():
                        violations.append({
                            "rule": rule.name,
                            "pattern": pattern,
                            "action": rule.action,
                        })

                        if self._event_bus:
                            self._event_bus.publish(
                                Event(
                                    type=EventType.POLICY_VIOLATION,
                                    payload={"rule": rule.name, "pattern": pattern},
                                    source="policy_check",
                                )
                            )

        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "redacted_content": self._redact_content(content) if violations else content,
        }

    def _redact_content(self, content: str) -> str:
        patterns = []
        for rule in self._rules:
            if rule.type == PolicyType.BLACKLIST and rule.action == "redact":
                patterns.extend(rule.conditions.get("patterns", []))

        redacted = content
        for pattern in patterns:
            import re

            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

        return redacted

    def check_file_safety(self, file_path: str) -> Dict[str, Any]:
        import os

        if not os.path.exists(file_path):
            return {"safe": True, "message": "File does not exist"}

        if os.path.islink(file_path):
            return {"safe": False, "message": "Symbolic links are not allowed"}

        real_path = os.path.realpath(file_path)
        restricted_paths = ["/etc", "/root", "/home", "C:\\Windows"]

        for restricted in restricted_paths:
            if real_path.startswith(restricted):
                return {"safe": False, "message": f"Access to restricted path: {restricted}"}

        return {"safe": True, "message": "File path is safe"}

    def list_rules(self) -> List[PolicyRule]:
        return self._rules
