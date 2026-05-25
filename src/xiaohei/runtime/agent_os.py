from typing import Dict, Any, Optional, List
from uuid import UUID
import asyncio
from loguru import logger

from ..types import Task, ExecutionResult, RuntimeMode, AgentConfig
from ..control import (
    FSMEngine, EventBus, Governance, PolicyController, BudgetManager,
    ModuleContracts, RuntimePolicy, CronScheduler, LifecycleManager, CredentialPool
)
from ..cognition import (
    TaskParser, Planner, FailureClassifier, Critic, ControlDecider, Reflector,
    DegradationManager, ContextEngine, ToolRegistry, AgentRuntime
)
from ..data import MemoryOS, MemoryStore, ContextGatherer, Compressor, CheckpointOS
from ..execution import (
    Executor, CapabilityGraph, MCPBus, Sandbox, SkillLibrary, SkillSystem
)
from ..validation import SyntaxCheck, SemanticCheck, RuntimeCheck, PolicyCheck
from ..observability import TraceManager, MetricsManager, LoggingManager, OpenTelemetryExporter, DynamicReplay
from ..gateway import WebServer, Gateway, CLI, ACPHandler
from .xiaohei_mode import XiaoHeiMode
from .hermes_mode import HermesMode


class AgentOS:
    def __init__(self, config: Optional[AgentConfig] = None):
        self._config = config or AgentConfig()
        self._running = False
        self._mode: RuntimeMode = RuntimeMode.WARM

        self._init_modules()
        logger.info("AgentOS initialized")

    def _init_modules(self):
        self._event_bus = EventBus()

        self._fsm_engine = FSMEngine()
        self._governance = Governance(self._event_bus)
        self._policy_controller = PolicyController(self._event_bus)
        self._budget_manager = BudgetManager(self._event_bus)
        self._module_contracts = ModuleContracts()
        self._runtime_policy = RuntimePolicy()
        self._cron_scheduler = CronScheduler()
        self._lifecycle_manager = LifecycleManager(self._event_bus)
        self._credential_pool = CredentialPool()

        self._memory_store = MemoryStore()
        self._memory_os = MemoryOS(self._memory_store)
        self._context_engine = ContextEngine()
        self._context_gatherer = ContextGatherer(self._memory_os, self._event_bus)
        self._compressor = Compressor()
        self._checkpoint_os = CheckpointOS(event_bus=self._event_bus)

        self._task_parser = TaskParser(self._event_bus)
        self._planner = Planner(self._event_bus)
        self._failure_classifier = FailureClassifier()
        self._critic = Critic(self._event_bus)
        self._control_decider = ControlDecider()
        self._reflector = Reflector()
        self._degradation_manager = DegradationManager()
        self._tool_registry = ToolRegistry(self._event_bus)
        self._agent_runtime = AgentRuntime(self._tool_registry, self._context_engine, self._event_bus)

        self._executor = Executor(self._tool_registry, self._event_bus)
        self._capability_graph = CapabilityGraph()
        self._mcp_bus = MCPBus(self._event_bus)
        self._sandbox = Sandbox()
        self._skill_library = SkillLibrary(event_bus=self._event_bus)
        self._skill_system = SkillSystem()

        self._syntax_check = SyntaxCheck(self._event_bus)
        self._semantic_check = SemanticCheck(self._event_bus)
        self._runtime_check = RuntimeCheck(self._event_bus)
        self._policy_check = PolicyCheck(self._event_bus)

        self._trace_manager = TraceManager(self._event_bus)
        self._metrics_manager = MetricsManager()
        self._logging_manager = LoggingManager(self._config.log_level)
        self._otel_exporter = OpenTelemetryExporter()
        self._dynamic_replay = DynamicReplay(event_bus=self._event_bus)

        self._web_server = WebServer(
            fsm_engine=self._fsm_engine,
            event_bus=self._event_bus,
        )
        self._gateway = Gateway(self._credential_pool, self._event_bus)
        self._cli = CLI(
            self._task_parser,
            self._planner,
            self._executor,
            self._critic,
            self._control_decider,
        )

        self._xiaohei_mode = XiaoHeiMode(self._event_bus)
        self._hermes_mode = HermesMode(self._tool_registry, self._context_engine, self._event_bus)

    async def start(self):
        self._running = True
        logger.info("AgentOS starting...")

        await self._memory_os.start()
        asyncio.create_task(self._cron_scheduler.start())

        logger.info("AgentOS started")

    async def stop(self):
        self._running = False
        logger.info("AgentOS stopping...")

        await self._memory_os.stop()
        self._cron_scheduler.stop()

        logger.info("AgentOS stopped")

    async def run_task(self, input_text: str, mode: str = "xiaohei") -> ExecutionResult:
        task = self._task_parser.parse(input_text)

        if mode == "xiaohei":
            return await self._xiaohei_mode.run(task)
        elif mode == "hermes":
            return await self._hermes_mode.run(task)
        else:
            return await self._xiaohei_mode.run(task)

    def set_mode(self, mode: RuntimeMode):
        self._mode = mode
        self._runtime_policy.set_mode(mode)
        logger.info(f"AgentOS mode changed to: {mode}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "mode": self._mode.value,
            "version": self._config.version,
            "modules": {
                "control": ["FSM", "EventBus", "Governance", "Policy", "Budget"],
                "cognition": ["TaskParser", "Planner", "Critic", "ControlDecider", "Reflector"],
                "data": ["MemoryOS", "MemoryStore", "ContextGatherer"],
                "execution": ["Executor", "CapabilityGraph", "MCPBus", "Sandbox"],
                "validation": ["SyntaxCheck", "SemanticCheck", "RuntimeCheck", "PolicyCheck"],
                "observability": ["Trace", "Metrics", "Logging", "OTel", "Replay"],
                "gateway": ["WebServer", "Gateway", "CLI"],
            },
        }

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics_manager.collect()

    def get_trace(self, task_id: UUID) -> Dict[str, Any]:
        return {}
