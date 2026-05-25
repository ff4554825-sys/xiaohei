from typing import List, Dict, List, Optional, Any
from uuid import UUID
from loguru import logger
from datetime import datetime

from ..types import GovernanceRule, AuditLog, Event, EventType


class Governance:
    def __init__(self, event_bus=None):
        self._rules: Dict[UUID, GovernanceRule] = {}
        self._audit_logs: List[AuditLog] = []
        self._event_bus = event_bus
        self._load_default_rules()
        logger.info("Governance initialized with {} rules", len(self._rules))

    def _load_default_rules(self):
        default_rules = [
            GovernanceRule(
                name="tool_whitelist",
                description="Only allow whitelisted tools",
                condition="tool.name in whitelist",
                action="allow",
                priority=1,
            ),
            GovernanceRule(
                name="rate_limit",
                description="Limit tool calls per minute",
                condition="rate > 60",
                action="block",
                priority=2,
            ),
            GovernanceRule(
                name="budget_control",
                description="Stop execution when budget exceeds",
                condition="budget.used > budget.limit",
                action="stop",
                priority=3,
            ),
            GovernanceRule(
                name="data_privacy",
                description="Block sensitive data access",
                condition="data.contains_sensitive",
                action="block",
                priority=1,
            ),
            GovernanceRule(
                name="output_filter",
                description="Filter harmful content",
                condition="output.contains_harmful",
                action="redact",
                priority=2,
            ),
            GovernanceRule(
                name="authentication",
                description="Require valid credentials",
                condition="credentials.valid",
                action="allow",
                priority=1,
            ),
            GovernanceRule(
                name="audit_logging",
                description="Log all critical operations",
                condition="operation.critical",
                action="log",
                priority=4,
            ),
        ]
        for rule in default_rules:
            self._rules[rule.id] = rule

    def add_rule(self, rule: GovernanceRule) -> None:
        self._rules[rule.id] = rule
        self._audit(f"rule_added", str(rule.id), "success", {"rule_name": rule.name})
        logger.info(f"Governance rule added: {rule.name}")

    def remove_rule(self, rule_id: UUID) -> bool:
        if rule_id in self._rules:
            rule = self._rules.pop(rule_id)
            self._audit(f"rule_removed", str(rule_id), "success", {"rule_name": rule.name})
            logger.info(f"Governance rule removed: {rule.name}")
            return True
        return False

    def get_rule(self, rule_id: UUID) -> Optional[GovernanceRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> List[GovernanceRule]:
        return list(self._rules.values())

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        results = []
        for rule in sorted(self._rules.values(), key=lambda r: r.priority):
            if not rule.enabled:
                continue

            try:
                condition_met = self._evaluate_condition(rule.condition, context)
                if condition_met:
                    action_result = self._execute_action(rule.action, context)
                    results.append({
                        "rule_id": str(rule.id),
                        "rule_name": rule.name,
                        "action": rule.action,
                        "result": action_result,
                    })
                    if rule.action in ["block", "stop"]:
                        break
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
                self._audit("rule_error", str(rule.id), "error", {"error": str(e)})

        return {"results": results, "allowed": not any(r["action"] in ["block", "stop"] for r in results)}

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        try:
            return eval(condition, {}, context)
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False

    def _execute_action(self, action: str, context: Dict[str, Any]) -> str:
        if action == "allow":
            return "allowed"
        elif action == "block":
            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.POLICY_VIOLATION,
                        payload={"context": context},
                        source="governance",
                    )
                )
            return "blocked"
        elif action == "stop":
            return "stopped"
        elif action == "redact":
            return "redacted"
        elif action == "log":
            self._audit("policy_log", context.get("operation"), "logged", context)
            return "logged"
        return "unknown"

    def _audit(self, action: str, target: Optional[str], result: str, details: Dict[str, Any]) -> None:
        audit_log = AuditLog(
            action=action,
            actor="governance",
            target=target,
            result=result,
            details=details,
        )
        self._audit_logs.append(audit_log)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.AUDIT,
                    payload={
                        "action": action,
                        "target": target,
                        "result": result,
                        "details": details,
                    },
                    source="governance",
                )
            )

        if len(self._audit_logs) > 10000:
            self._audit_logs = self._audit_logs[-5000:]

    def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        return self._audit_logs[-limit:]

    def reload_rules(self) -> None:
        self._load_default_rules()
        self._audit("rules_reloaded", None, "success", {})
        logger.info("Governance rules reloaded")
