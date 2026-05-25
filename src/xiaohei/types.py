from typing import List, Any, Dict, List, Optional, Type, Union, Callable, Awaitable
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4


class AgentPhase(str, Enum):
    IDLE = "idle"
    PARSE_TASK = "parse_task"
    DIVERGE = "diverge"
    SEARCH = "search"
    SCORER = "scorer"
    DECOMPOSE = "decompose"
    EXECUTE = "execute"
    VERIFY = "verify"
    CRITIC = "critic"
    REFLECT = "reflect"
    RETRY = "retry"
    FINISH = "finish"
    ERROR = "error"
    HANDOFF = "handoff"


class EventType(str, Enum):
    TASK_START = "task.start"
    TASK_END = "task.end"
    PHASE_CHANGE = "phase.change"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    ERROR = "error"
    WARNING = "warning"
    METRIC = "metric"
    LOG = "log"
    AUDIT = "audit"
    BUDGET_UPDATE = "budget.update"
    POLICY_VIOLATION = "policy.violation"
    MEMORY_ACCESS = "memory.access"
    CHECKPOINT = "checkpoint"
    REPLAY = "replay"


class TaskType(str, Enum):
    INFORMATION = "information"
    CREATION = "creation"
    ANALYSIS = "analysis"
    TRANSFORMATION = "transformation"
    ACTION = "action"
    RESEARCH = "research"
    EDUCATION = "education"
    DEBUG = "debug"


class TaskConstraint(BaseModel):
    max_tokens: Optional[int] = None
    max_time: Optional[int] = None
    max_cost: Optional[float] = None
    required_skills: List[str] = []
    forbidden_skills: List[str] = []


class TaskRisk(BaseModel):
    level: str = "low"
    categories: List[str] = []
    mitigation: Optional[str] = None


class TaskComplexity(BaseModel):
    score: float = 0.0
    factors: Dict[str, float] = {}


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: TaskType
    input: str
    constraints: TaskConstraint = Field(default_factory=TaskConstraint)
    risk: TaskRisk = Field(default_factory=TaskRisk)
    complexity: TaskComplexity = Field(default_factory=TaskComplexity)
    context: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ToolCall(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tool_name: str
    args: Dict[str, Any]
    task_id: UUID
    created_at: datetime = Field(default_factory=datetime.now)


class ToolResult(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tool_call_id: UUID
    success: bool
    output: Any
    error: Optional[str] = None
    completed_at: datetime = Field(default_factory=datetime.now)


class MemoryLevel(str, Enum):
    SCRATCHPAD = "scratchpad"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    level: MemoryLevel
    key: str
    value: Any
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    accessed_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class PolicyType(str, Enum):
    WHITELIST = "whitelist"
    BLACKLIST = "blacklist"
    RATE_LIMIT = "rate_limit"
    BUDGET = "budget"


class PolicyRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: PolicyType
    name: str
    description: str
    conditions: Dict[str, Any]
    action: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class BudgetDimension(str, Enum):
    TOKENS = "tokens"
    TIME = "time"
    COST = "cost"
    CALLS = "calls"


class Budget(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    dimensions: Dict[BudgetDimension, float] = {}
    limits: Dict[BudgetDimension, float] = {}
    soft_limit_percent: float = 0.8
    expansion_percent: float = 0.3
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Span(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_id: Optional[UUID] = None
    name: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    attributes: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class Metric(BaseModel):
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = {}
    timestamp: datetime = Field(default_factory=datetime.now)


class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: EventType
    payload: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "unknown"


class ExecutionProfile(str, Enum):
    READ_ONLY = "read_only"
    SANDBOX = "sandbox"
    ISOLATED = "isolated"
    FULL = "full"
    DANGEROUS = "dangerous"


class Skill(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    config: Dict[str, Any] = {}
    handler: str
    category: str = "general"
    version: str = "1.0.0"
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class Capability(BaseModel):
    name: str
    description: str
    skills: List[str] = []
    dependencies: List[str] = []
    fallback: Optional[str] = None


class Checkpoint(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    state: Dict[str, Any] = {}
    memory_snapshot: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)


class FailureType(str, Enum):
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_ERROR = "semantic_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class FailurePattern(BaseModel):
    type: FailureType
    pattern: str
    recovery_strategy: str
    confidence: float = 0.0


class DecisionType(str, Enum):
    RETRY = "retry"
    REFLECT = "reflect"
    FALLBACK = "fallback"
    FINISH = "finish"
    HANDOFF = "handoff"


class Decision(BaseModel):
    type: DecisionType
    reason: str
    params: Dict[str, Any] = {}


class ProviderType(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    MINIMAX = "minimax"
    OLLAMA = "ollama"


class Credential(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    provider: ProviderType
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class ExecutionResult(BaseModel):
    success: bool
    output: Any
    error: Optional[str] = None
    trace_id: UUID
    metrics: List[Metric] = []


class ScoredPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    plan: List[Dict[str, Any]]
    scores: Dict[str, float] = {}
    total_score: float = 0.0


class Reflection(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    analysis: str
    root_cause: str
    suggestions: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)


class CompressedContext(BaseModel):
    original_length: int
    compressed_length: int
    summary: str
    key_points: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class GovernanceRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    condition: str
    action: str
    priority: int = 1
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class AuditLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    action: str
    actor: str
    target: Optional[str] = None
    result: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = {}


class RuntimeMode(str, Enum):
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class ModuleStatus(BaseModel):
    name: str
    status: str = "running"
    mode: RuntimeMode = RuntimeMode.WARM
    metrics: Dict[str, Any] = {}


class AgentConfig(BaseModel):
    name: str = "XiaoHei"
    description: str = "Agent OS"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
