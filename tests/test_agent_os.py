import pytest
import asyncio
from uuid import uuid4

from src.xiaohei.runtime import AgentOS
from src.xiaohei.types import Task, TaskType, AgentPhase
from src.xiaohei.control import FSMEngine


class TestAgentOS:
    def test_init(self):
        agent_os = AgentOS()
        assert agent_os is not None
        assert agent_os.get_status()["running"] == False

    @pytest.mark.asyncio
    async def test_start_stop(self):
        agent_os = AgentOS()
        await agent_os.start()
        assert agent_os.get_status()["running"] == True
        await agent_os.stop()
        assert agent_os.get_status()["running"] == False


class TestFSMEngine:
    def test_initial_state(self):
        fsm = FSMEngine()
        assert fsm.get_current_phase() == AgentPhase.IDLE

    def test_valid_transition(self):
        fsm = FSMEngine()
        result = fsm.transition(AgentPhase.PARSE_TASK)
        assert result == True
        assert fsm.get_current_phase() == AgentPhase.PARSE_TASK

    def test_invalid_transition(self):
        fsm = FSMEngine()
        result = fsm.transition(AgentPhase.EXECUTE)
        assert result == False
        assert fsm.get_current_phase() == AgentPhase.IDLE


class TestTaskParser:
    def test_parse_information(self):
        from src.xiaohei.cognition import TaskParser

        parser = TaskParser()
        task = parser.parse("What is the capital of France?")
        assert task.type == TaskType.INFORMATION

    def test_parse_creation(self):
        from src.xiaohei.cognition import TaskParser

        parser = TaskParser()
        task = parser.parse("Write a Python function to sort a list")
        assert task.type == TaskType.CREATION

    def test_parse_analysis(self):
        from src.xiaohei.cognition import TaskParser

        parser = TaskParser()
        task = parser.parse("Analyze the sales data")
        assert task.type == TaskType.ANALYSIS


class TestPlanner:
    def test_diverge(self):
        from src.xiaohei.cognition import Planner
        from src.xiaohei.types import Task, TaskType

        planner = Planner()
        task = Task(type=TaskType.CREATION, input="Create a report")
        plans = planner.diverge(task)
        assert len(plans) > 0

    def test_score(self):
        from src.xiaohei.cognition import Planner
        from src.xiaohei.types import Task, TaskType

        planner = Planner()
        task = Task(type=TaskType.CREATION, input="Create a report")
        plans = planner.diverge(task)
        scored = planner.score(plans, task)
        assert len(scored) == len(plans)


class TestMemoryOS:
    @pytest.mark.asyncio
    async def test_memory_write_read(self):
        from src.xiaohei.data import MemoryOS, MemoryStore
        from src.xiaohei.types import MemoryLevel

        memory_store = MemoryStore(":memory:")
        memory_os = MemoryOS(memory_store)

        memory_os.write(MemoryLevel.SCRATCHPAD, "test_key", "test_value")
        result = memory_os.read(MemoryLevel.SCRATCHPAD, "test_key")
        assert result == "test_value"

        await memory_os.stop()


class TestEventBus:
    def test_publish_subscribe(self):
        from src.xiaohei.control import EventBus
        from src.xiaohei.types import Event, EventType

        event_bus = EventBus()
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe("test.*", handler)
        event = Event(type=EventType.LOG, payload={"message": "test"})
        event_bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.LOG
