from typing import List, Dict, List, Set, Optional, Any
from uuid import UUID
from loguru import logger

from ..types import PolicyRule, PolicyType, Event, EventType


class PolicyController:
    def __init__(self, event_bus=None):
        self._rules: Dict[UUID, PolicyRule] = {}
        self._whitelist: Set[str] = set()
        self._blacklist: Set[str] = set()
        self._rate_limits: Dict[str, int] = {}
        self._event_bus = event_bus
        logger.info("PolicyController initialized")

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules[rule.id] = rule

        if rule.type == PolicyType.WHITELIST:
            for item in rule.conditions.get("items", []):
                self._whitelist.add(item)
        elif rule.type == PolicyType.BLACKLIST:
            for item in rule.conditions.get("items", []):
                self._blacklist.add(item)
        elif rule.type == PolicyType.RATE_LIMIT:
            self._rate_limits[rule.name] = rule.conditions.get("limit", 60)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={"message": f"Policy rule added: {rule.name}"},
                    source="policy",
                )
            )
        logger.info(f"Policy rule added: {rule.name}")

    def remove_rule(self, rule_id: UUID) -> bool:
        if rule_id in self._rules:
            rule = self._rules.pop(rule_id)

            if rule.type == PolicyType.WHITELIST:
                for item in rule.conditions.get("items", []):
                    self._whitelist.discard(item)
            elif rule.type == PolicyType.BLACKLIST:
                for item in rule.conditions.get("items", []):
                    self._blacklist.discard(item)
            elif rule.type == PolicyType.RATE_LIMIT:
                self._rate_limits.pop(rule.name, None)

            logger.info(f"Policy rule removed: {rule.name}")
            return True
        return False

    def check_whitelist(self, tool_name: str) -> bool:
        if not self._whitelist:
            return True
        return tool_name in self._whitelist

    def check_blacklist(self, tool_name: str) -> bool:
        return tool_name in self._blacklist

    def is_tool_allowed(self, tool_name: str) -> bool:
        if self.check_blacklist(tool_name):
            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.POLICY_VIOLATION,
                        payload={"tool": tool_name, "reason": "blacklisted"},
                        source="policy",
                    )
                )
            return False

        if not self.check_whitelist(tool_name):
            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.POLICY_VIOLATION,
                        payload={"tool": tool_name, "reason": "not whitelisted"},
                        source="policy",
                    )
                )
            return False

        return True

    def get_rate_limit(self, key: str) -> int:
        return self._rate_limits.get(key, 60)

    def list_rules(self) -> List[PolicyRule]:
        return list(self._rules.values())

    def clear_rules(self) -> None:
        self._rules.clear()
        self._whitelist.clear()
        self._blacklist.clear()
        self._rate_limits.clear()
        logger.info("All policy rules cleared")
