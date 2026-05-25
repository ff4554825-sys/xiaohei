from typing import List, Dict, List, Any, Optional
from uuid import UUID, uuid4
from loguru import logger

from ..types import Task, ScoredPlan, Event, EventType


class Planner:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        logger.info("Planner initialized")

    def diverge(self, task: Task) -> List[Dict[str, Any]]:
        plans = []

        if task.type.value == "creation":
            plans = self._create_plans(task)
        elif task.type.value == "analysis":
            plans = self._analyze_plans(task)
        elif task.type.value == "action":
            plans = self._action_plans(task)
        else:
            plans = self._default_plans(task)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Generated {len(plans)} plans for task: {task.id}",
                    },
                    source="planner",
                )
            )

        logger.info(f"Generated {len(plans)} plans for task: {task.id}")
        return plans

    def _create_plans(self, task: Task) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "name": "直接生成",
                "steps": ["分析需求", "生成内容", "验证输出"],
                "estimated_cost": 1,
            },
            {
                "id": str(uuid4()),
                "name": "迭代生成",
                "steps": ["分析需求", "生成初稿", "审核修改", "生成终稿", "验证输出"],
                "estimated_cost": 2,
            },
        ]

    def _analyze_plans(self, task: Task) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "name": "快速分析",
                "steps": ["收集信息", "简单分析", "输出结果"],
                "estimated_cost": 1,
            },
            {
                "id": str(uuid4()),
                "name": "深度分析",
                "steps": ["收集信息", "深入分析", "对比评估", "生成报告", "验证准确性"],
                "estimated_cost": 3,
            },
        ]

    def _action_plans(self, task: Task) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "name": "直接执行",
                "steps": ["验证权限", "执行操作", "确认结果"],
                "estimated_cost": 1,
            },
            {
                "id": str(uuid4()),
                "name": "安全执行",
                "steps": ["验证权限", "备份数据", "执行操作", "确认结果", "记录日志"],
                "estimated_cost": 2,
            },
        ]

    def _default_plans(self, task: Task) -> List[Dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "name": "标准流程",
                "steps": ["理解问题", "查找信息", "生成答案", "验证准确性"],
                "estimated_cost": 1,
            }
        ]

    def score(self, plans: List[Dict[str, Any]], task: Task) -> List[ScoredPlan]:
        scored_plans = []

        for plan in plans:
            scores = self._calculate_scores(plan, task)
            total_score = sum(scores.values()) / len(scores)

            scored_plan = ScoredPlan(
                plan=plan["steps"],
                scores=scores,
                total_score=total_score,
            )
            scored_plans.append(scored_plan)

        logger.info(f"Scored {len(scored_plans)} plans")
        return scored_plans

    def _calculate_scores(self, plan: Dict[str, Any], task: Task) -> Dict[str, float]:
        scores = {}

        steps = plan["steps"]
        cost = plan.get("estimated_cost", 1)

        scores["efficiency"] = min(1.0, 10 / len(steps))
        scores["risk_mitigation"] = 0.8 if len(steps) > 3 else 0.5
        scores["cost_effectiveness"] = min(1.0, 3 / cost)
        scores["completeness"] = 0.9 if len(steps) >= 4 else 0.7
        scores["speed"] = min(1.0, 5 / len(steps))

        return scores

    def select(self, scored_plans: List[ScoredPlan]) -> Optional[ScoredPlan]:
        if not scored_plans:
            return None

        best_plan = max(scored_plans, key=lambda p: p.total_score)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Selected plan with score: {best_plan.total_score}",
                    },
                    source="planner",
                )
            )

        logger.info(f"Selected plan with score: {best_plan.total_score}")
        return best_plan
