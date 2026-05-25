from typing import Dict, Optional, Any
from uuid import UUID
from loguru import logger
from datetime import datetime

from ..types import Budget, BudgetDimension, Event, EventType


class BudgetManager:
    def __init__(self, event_bus=None):
        self._budgets: Dict[UUID, Budget] = {}
        self._default_budget_id: Optional[UUID] = None
        self._event_bus = event_bus
        logger.info("BudgetManager initialized")

    def create_budget(self, limits: Dict[BudgetDimension, float]) -> Budget:
        budget = Budget(
            limits=limits,
            dimensions={dim: 0.0 for dim in limits.keys()},
        )
        self._budgets[budget.id] = budget

        if not self._default_budget_id:
            self._default_budget_id = budget.id

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.BUDGET_UPDATE,
                    payload={"budget_id": str(budget.id), "action": "created"},
                    source="budget",
                )
            )

        logger.info(f"Budget created: {budget.id}")
        return budget

    def get_budget(self, budget_id: Optional[UUID] = None) -> Optional[Budget]:
        if budget_id:
            return self._budgets.get(budget_id)
        if self._default_budget_id:
            return self._budgets.get(self._default_budget_id)
        return None

    def allocate(self, dimension: BudgetDimension, amount: float, budget_id: Optional[UUID] = None) -> bool:
        budget = self.get_budget(budget_id)
        if not budget:
            logger.error("No budget found")
            return False

        if dimension not in budget.dimensions:
            budget.dimensions[dimension] = 0.0

        current = budget.dimensions[dimension]
        limit = budget.limits.get(dimension, float("inf"))
        soft_limit = limit * budget.soft_limit_percent

        if current + amount > limit:
            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.POLICY_VIOLATION,
                        payload={
                            "dimension": dimension.value,
                            "current": current,
                            "amount": amount,
                            "limit": limit,
                            "reason": "hard limit exceeded",
                        },
                        source="budget",
                    )
                )
            logger.warning(f"Budget hard limit exceeded: {dimension}")
            return False

        if current + amount > soft_limit:
            expansion_limit = limit * (1 + budget.expansion_percent)
            if current + amount <= expansion_limit:
                if self._event_bus:
                    self._event_bus.publish(
                        Event(
                            type=EventType.BUDGET_UPDATE,
                            payload={
                                "dimension": dimension.value,
                                "current": current,
                                "amount": amount,
                                "limit": limit,
                                "status": "negotiated_expansion",
                            },
                            source="budget",
                        )
                    )
                logger.info(f"Budget expansion used: {dimension}")
            else:
                if self._event_bus:
                    self._event_bus.publish(
                        Event(
                            type=EventType.WARNING,
                            payload={
                                "dimension": dimension.value,
                                "current": current,
                                "amount": amount,
                                "soft_limit": soft_limit,
                            },
                            source="budget",
                        )
                    )

        budget.dimensions[dimension] = current + amount
        budget.updated_at = datetime.now()

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.BUDGET_UPDATE,
                    payload={
                        "dimension": dimension.value,
                        "used": budget.dimensions[dimension],
                        "limit": limit,
                    },
                    source="budget",
                )
            )

        return True

    def get_usage(self, budget_id: Optional[UUID] = None) -> Dict[BudgetDimension, float]:
        budget = self.get_budget(budget_id)
        return budget.dimensions if budget else {}

    def reset(self, budget_id: Optional[UUID] = None) -> None:
        budget = self.get_budget(budget_id)
        if budget:
            for dim in budget.dimensions:
                budget.dimensions[dim] = 0.0
            budget.updated_at = datetime.now()
            logger.info(f"Budget reset: {budget.id}")

    def check_budget(self, dimension: BudgetDimension, amount: float, budget_id: Optional[UUID] = None) -> bool:
        budget = self.get_budget(budget_id)
        if not budget:
            return True

        current = budget.dimensions.get(dimension, 0.0)
        limit = budget.limits.get(dimension, float("inf"))

        return current + amount <= limit
