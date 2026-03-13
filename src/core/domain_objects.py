"""
Core domain objects used across the entire COS-AA system.
Pure Pydantic models with no infrastructure dependencies.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════


class AgentType(str, Enum):
    HUB = "HUB"
    PLANNING = "PLANNING"
    LEARNING = "LEARNING"
    MONITORING = "MONITORING"
    KNOWLEDGE = "KNOWLEDGE"
    CREATED = "CREATED"


class AgentInstanceStatus(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class OODAPhase(str, Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    ORIENTING = "ORIENTING"
    DECIDING = "DECIDING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    ACTING = "ACTING"
    REVIEWING = "REVIEWING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InputModality(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    METRIC = "METRIC"


class InputSource(str, Enum):
    USER = "USER"
    TOOL = "TOOL"
    AGENT = "AGENT"
    SENSOR = "SENSOR"
    SCHEDULED = "SCHEDULED"


class MemoryTier(str, Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"


class MemorySourceType(str, Enum):
    EPISODIC = "EPISODIC"
    DOCUMENT = "DOCUMENT"
    WEB = "WEB"
    TOOL_RESULT = "TOOL_RESULT"
    USER_INPUT = "USER_INPUT"


class EpisodicEventType(str, Enum):
    TASK_START = "TASK_START"
    TASK_COMPLETE = "TASK_COMPLETE"
    TOOL_USE = "TOOL_USE"
    ERROR = "ERROR"
    USER_FEEDBACK = "USER_FEEDBACK"
    AGENT_SPAWN = "AGENT_SPAWN"


class FailureType(str, Enum):
    RETRIABLE = "RETRIABLE"
    NON_RETRIABLE = "NON_RETRIABLE"
    DEGRADED = "DEGRADED"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    OVERLOAD = "OVERLOAD"


class AgentDefinitionStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ═══════════════════════════════════════════════════════════════
# CORE OBJECTS
# ═══════════════════════════════════════════════════════════════


class AgentRef(BaseModel):
    """Reference to a specific agent instance."""

    agent_id: UUID = Field(default_factory=uuid4)
    agent_type: AgentType = AgentType.HUB
    instance_id: str = ""


class GoalObject(BaseModel):
    """Represents the current active goal of an OODA cycle."""

    goal_id: UUID = Field(default_factory=uuid4)
    description: str
    success_criteria: list[str] = []
    priority: Priority = Priority.NORMAL
    max_iterations: int = 5
    timeout_seconds: int = 120


class ObservationObject(BaseModel):
    """A single normalized observation from any input source."""

    observation_id: UUID = Field(default_factory=uuid4)
    source_type: InputSource
    content: Any
    raw_content: str = ""
    modality: InputModality = InputModality.TEXT
    relevance_score: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = {}


class ObservationSet(BaseModel):
    """Ordered collection of observations, highest relevance first."""

    observations: list[ObservationObject] = []
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryFragment(BaseModel):
    """A piece of retrieved memory from any tier."""

    fragment_id: UUID = Field(default_factory=uuid4)
    tier: MemoryTier
    content: str
    summary: str = ""
    relevance_score: float = 0.0
    source_type: MemorySourceType = MemorySourceType.EPISODIC
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = []


class CapabilityDescriptor(BaseModel):
    """Describes what an agent can do."""

    task_type: str
    required_tool_names: list[str] = []
    average_completion_time_seconds: float = 0.0


class CoTStep(BaseModel):
    """One step in a Chain-of-Thought reasoning chain."""

    step_number: int
    step_name: str
    reasoning: str
    confidence: float = 1.0


class CoTOption(BaseModel):
    """One option generated during CoT reasoning."""

    name: str
    approach: str
    pros: list[str] = []
    cons: list[str] = []
    risk_level: RiskLevel = RiskLevel.MEDIUM


class SituationModel(BaseModel):
    """Output of the ORIENT phase — the result of CoT reasoning."""

    cot_chain: list[CoTStep] = []
    situation_summary: str
    intent_interpretation: str = ""
    knowledge_gaps: list[str] = []
    options: list[CoTOption] = []
    recommended_option: str = ""
    confidence: float = 0.5
    requires_human_confirmation: bool = False


class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 60.0


class ActionStep(BaseModel):
    """A single step in an action plan."""

    step_id: UUID = Field(default_factory=uuid4)
    step_number: int
    agent_type: AgentType
    tool_name: str | None = None
    input_params: dict[str, Any] = {}
    expected_output_schema: dict | None = None
    timeout_seconds: int = 60
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    depends_on: list[UUID] = []
    is_critical: bool = True


class ActionPlan(BaseModel):
    """The full execution plan produced by the DECIDE phase."""

    plan_id: UUID = Field(default_factory=uuid4)
    goal_id: UUID
    steps: list[ActionStep] = []


class StepResult(BaseModel):
    """Outcome of a single action step."""

    step_id: UUID
    success: bool
    output: Any = None
    error_message: str | None = None
    duration_ms: float = 0.0


class ExecutionResult(BaseModel):
    """Aggregated outcome of the ACT phase."""

    plan_id: UUID
    step_results: list[StepResult] = []
    all_critical_succeeded: bool = True
    total_duration_ms: float = 0.0


class FailedReason(BaseModel):
    """Why an OODA cycle or step failed."""

    failure_type: FailureType
    message: str
    agent_type: AgentType | None = None
    task_type: str | None = None


class CycleResult(BaseModel):
    """Final outcome of one OODA iteration."""

    cycle_id: UUID = Field(default_factory=uuid4)
    cycle_number: int = 1
    goal_achieved: bool = False
    evidence: str = ""
    failed_reason: FailedReason | None = None
    next_observations: ObservationSet | None = None
    execution_result: ExecutionResult | None = None


class ToolSpec(BaseModel):
    """Describes a tool usable by an agent."""

    tool_name: str
    tool_type: str  # API, CODE_INTERPRETER, FILE_IO, WEB_SEARCH, CUSTOM
    config: dict[str, Any] = {}
    permissions_required: list[str] = []


class MemoryAccessSpec(BaseModel):
    can_read_semantic: bool = True
    can_write_episodic: bool = True
    can_read_procedural: bool = True


class ResourceLimits(BaseModel):
    max_concurrent_tasks: int = 5
    max_llm_tokens_per_task: int = 8000
    max_tool_calls_per_task: int = 10
    timeout_seconds: int = 120


class AgentDefinition(BaseModel):
    """Full definition of an auto-created or manually defined agent type."""

    definition_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    agent_type_name: str
    agent_type_id: UUID = Field(default_factory=uuid4)
    purpose: str
    trigger_conditions: list[str] = []
    tools: list[ToolSpec] = []
    system_prompt: str = ""
    model_override: str | None = None
    memory_access: MemoryAccessSpec = Field(default_factory=MemoryAccessSpec)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    created_by: str = "SYSTEM_AUTO"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AgentDefinitionStatus = AgentDefinitionStatus.DRAFT


class ExecutionContext(BaseModel):
    """Context passed to tool execution."""

    tenant_id: UUID
    user_id: UUID | None = None
    session_id: UUID | None = None
    trace_id: UUID = Field(default_factory=uuid4)
    span_id: UUID = Field(default_factory=uuid4)
    sandbox_config: dict[str, Any] = {}


class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error_message: str | None = None
    duration_ms: float = 0.0


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []


class HealthStatus(BaseModel):
    healthy: bool
    checks: dict[str, bool] = {}
    message: str = ""


class ContextBundle(BaseModel):
    """Assembled context for the ORIENT phase CoT reasoning."""

    current_observations: ObservationSet
    relevant_memories: list[MemoryFragment] = []
    active_goal: GoalObject
    agent_capabilities: list[CapabilityDescriptor] = []
    available_tools: list[str] = []
    constraints: dict[str, Any] = {}
    prior_cycle_outcomes: list[CycleResult] = []
