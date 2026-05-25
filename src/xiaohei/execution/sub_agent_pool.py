from typing import List, Dict, List, Any, Optional
from uuid import UUID, uuid4
import asyncio
from loguru import logger

from ..types import Task, ExecutionResult, Event, EventType


class SubAgent:
    def __init__(self, name: str, endpoint: str):
        self.id = uuid4()
        self.name = name
        self.endpoint = endpoint
        self.active = True
        self.task_count = 0
        self.last_used = None


class SubAgentPool:
    def __init__(self, event_bus=None):
        self._agents: Dict[UUID, SubAgent] = {}
        self._event_bus = event_bus
        logger.info("SubAgentPool initialized")

    def add_agent(self, name: str, endpoint: str) -> UUID:
        agent = SubAgent(name, endpoint)
        self._agents[agent.id] = agent

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={"message": f"Sub-agent added: {name}", "endpoint": endpoint},
                    source="sub_agent_pool",
                )
            )

        logger.info(f"Sub-agent added: {name}")
        return agent.id

    def remove_agent(self, agent_id: UUID) -> bool:
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            logger.info(f"Sub-agent removed: {agent.name}")
            return True
        return False

    def get_agent(self, agent_id: UUID) -> Optional[SubAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[SubAgent]:
        return list(self._agents.values())

    def get_active_agents(self) -> List[SubAgent]:
        return [a for a in self._agents.values() if a.active]

    async def dispatch(self, task: Task) -> ExecutionResult:
        agent = self._select_agent(task)
        if not agent:
            return ExecutionResult(
                success=False,
                output=None,
                error="No available sub-agents",
                trace_id=task.id,
            )

        agent.task_count += 1
        agent.last_used = asyncio.get_event_loop().time()

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Task dispatched to sub-agent: {agent.name}",
                        "task_id": str(task.id),
                    },
                    source="sub_agent_pool",
                )
            )

        try:
            result = await self._send_to_agent(agent, task)
            return result
        except Exception as e:
            agent.active = False
            logger.error(f"Sub-agent {agent.name} failed: {e}")

            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.ERROR,
                        payload={"agent": agent.name, "error": str(e)},
                        source="sub_agent_pool",
                    )
                )

            return ExecutionResult(
                success=False,
                output=None,
                error=str(e),
                trace_id=task.id,
            )

    def _select_agent(self, task: Task) -> Optional[SubAgent]:
        active_agents = self.get_active_agents()
        if not active_agents:
            return None

        return min(active_agents, key=lambda a: a.task_count)

    async def _send_to_agent(self, agent: SubAgent, task: Task) -> ExecutionResult:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    agent.endpoint,
                    json={
                        "task_id": str(task.id),
                        "type": task.type.value,
                        "input": task.input,
                        "context": task.context,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()

                return ExecutionResult(
                    success=data.get("success", False),
                    output=data.get("output"),
                    error=data.get("error"),
                    trace_id=task.id,
                )
        except Exception as e:
            raise e

    def get_stats(self) -> Dict[str, Any]:
        active = len(self.get_active_agents())
        total = len(self._agents)
        total_tasks = sum(a.task_count for a in self._agents.values())

        return {
            "total_agents": total,
            "active_agents": active,
            "total_tasks_dispatched": total_tasks,
        }

    def health_check(self) -> Dict[str, Any]:
        results = {}

        for agent in self._agents.values():
            results[agent.name] = {"active": agent.active, "task_count": agent.task_count}

        return results
