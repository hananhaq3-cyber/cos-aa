"""
Hub execution state: tracks OODA cycle progress, checkpoints to Redis.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.core.domain_objects import OODAPhase
from src.db.redis_client import RedisClient, redis_client

CYCLE_TTL_SECONDS = 600


class CycleState:
    """Serializable state of a single OODA cycle."""

    def __init__(
        self,
        cycle_id: UUID | None = None,
        tenant_id: UUID | None = None,
        session_id: UUID | None = None,
        trace_id: UUID | None = None,
        phase: OODAPhase = OODAPhase.IDLE,
        iteration: int = 0,
        max_iterations: int = 5,
        goal_description: str = "",
        started_at: str | None = None,
    ):
        self.cycle_id = cycle_id or uuid4()
        self.tenant_id = tenant_id
        self.session_id = session_id
        self.trace_id = trace_id or uuid4()
        self.phase = phase
        self.iteration = iteration
        self.max_iterations = max_iterations
        self.goal_description = goal_description
        self.started_at = started_at or datetime.now(timezone.utc).isoformat()
        self.phase_data: dict = {}
        # Human confirmation fields
        self.confirmation_requested_at: str | None = None
        self.confirmation_action_plan: dict | None = None

    def await_confirmation(self, action_plan: object) -> None:
        """Transition state to AWAITING_CONFIRMATION with the action plan."""
        self.phase = OODAPhase.AWAITING_CONFIRMATION
        self.confirmation_requested_at = datetime.now(timezone.utc).isoformat()
        if hasattr(action_plan, "model_dump"):
            self.confirmation_action_plan = action_plan.model_dump(mode="json")
        else:
            self.confirmation_action_plan = {"summary": str(action_plan)}

    def to_dict(self) -> dict:
        return {
            "cycle_id": str(self.cycle_id),
            "tenant_id": str(self.tenant_id),
            "session_id": str(self.session_id),
            "trace_id": str(self.trace_id),
            "phase": self.phase.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "goal_description": self.goal_description,
            "started_at": self.started_at,
            "phase_data": self.phase_data,
            "confirmation_requested_at": self.confirmation_requested_at,
            "confirmation_action_plan": self.confirmation_action_plan,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CycleState":
        state = cls(
            cycle_id=UUID(data["cycle_id"]),
            tenant_id=UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            session_id=UUID(data["session_id"]) if data.get("session_id") else None,
            trace_id=UUID(data["trace_id"]),
            phase=OODAPhase(data["phase"]),
            iteration=data["iteration"],
            max_iterations=data["max_iterations"],
            goal_description=data["goal_description"],
            started_at=data["started_at"],
        )
        state.phase_data = data.get("phase_data", {})
        state.confirmation_requested_at = data.get("confirmation_requested_at")
        state.confirmation_action_plan = data.get("confirmation_action_plan")
        return state


class HubStateManager:
    """Manages OODA cycle state in Redis for persistence and HA failover."""

    async def save(self, state: CycleState) -> None:
        key = RedisClient.hub_state_key(state.tenant_id, state.cycle_id)
        await redis_client.set_json(key, state.to_dict(), ttl_seconds=CYCLE_TTL_SECONDS)

    async def load(self, tenant_id: UUID, cycle_id: UUID) -> CycleState | None:
        key = RedisClient.hub_state_key(tenant_id, cycle_id)
        data = await redis_client.get_json(key)
        if data is None:
            return None
        return CycleState.from_dict(data)

    async def delete(self, tenant_id: UUID, cycle_id: UUID) -> None:
        key = RedisClient.hub_state_key(tenant_id, cycle_id)
        await redis_client.client.delete(key)

    async def transition(self, state: CycleState, new_phase: OODAPhase) -> None:
        state.phase = new_phase
        await self.save(state)


hub_state_manager = HubStateManager()
