"""
Domain-specific exception hierarchy.
All exceptions extend CosAAException so callers can catch broadly or specifically.
"""


class CosAAException(Exception):
    """Base exception for the COS-AA system."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# --- Auth ---


class AuthenticationError(CosAAException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTH_FAILED")


class AuthorizationError(CosAAException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="FORBIDDEN")


# --- Tenant ---


class TenantNotFoundError(CosAAException):
    def __init__(self, tenant_id: str):
        super().__init__(f"Tenant {tenant_id} not found", code="TENANT_NOT_FOUND")


class QuotaExceededError(CosAAException):
    def __init__(self, resource: str, tenant_id: str):
        super().__init__(
            f"Quota exceeded for {resource} (tenant {tenant_id})",
            code="QUOTA_EXCEEDED",
        )


# --- Agent ---


class AgentNotAvailableError(CosAAException):
    def __init__(self, agent_type: str):
        super().__init__(
            f"No available instance of agent type '{agent_type}'",
            code="AGENT_UNAVAILABLE",
        )


class AgentExecutionError(CosAAException):
    def __init__(self, agent_id: str, reason: str):
        super().__init__(
            f"Agent {agent_id} execution failed: {reason}",
            code="AGENT_EXEC_FAILED",
        )


class CapabilityMissingError(CosAAException):
    def __init__(self, task_type: str):
        super().__init__(
            f"No agent can handle task type '{task_type}'",
            code="CAPABILITY_MISSING",
        )


# --- OODA ---


class OODATimeoutError(CosAAException):
    def __init__(self, cycle_id: str, phase: str):
        super().__init__(
            f"OODA cycle {cycle_id} timed out in {phase} phase",
            code="OODA_TIMEOUT",
        )


class MaxIterationsExceededError(CosAAException):
    def __init__(self, cycle_id: str, max_iter: int):
        super().__init__(
            f"OODA cycle {cycle_id} exceeded max iterations ({max_iter})",
            code="MAX_ITERATIONS",
        )


class DuplicateTaskError(CosAAException):
    def __init__(self, idempotency_key: str):
        super().__init__(
            f"Duplicate task detected (idempotency_key={idempotency_key})",
            code="DUPLICATE_TASK",
        )


class HumanConfirmationRequired(CosAAException):
    """Raised during DECIDE when the action plan requires human approval."""

    def __init__(self, action_plan: object):
        self.action_plan = action_plan
        super().__init__(
            "Action plan requires human confirmation before execution",
            code="HUMAN_CONFIRMATION_REQUIRED",
        )


# --- Memory ---


class MemoryWriteError(CosAAException):
    def __init__(self, tier: str, reason: str):
        super().__init__(
            f"Failed to write to {tier} memory: {reason}",
            code="MEMORY_WRITE_FAILED",
        )


class MemoryRetrievalError(CosAAException):
    def __init__(self, tier: str, reason: str):
        super().__init__(
            f"Failed to retrieve from {tier} memory: {reason}",
            code="MEMORY_READ_FAILED",
        )


# --- LLM ---


class LLMCallError(CosAAException):
    def __init__(self, provider: str, reason: str):
        super().__init__(
            f"LLM call to {provider} failed: {reason}",
            code="LLM_CALL_FAILED",
        )


class CoTParsingError(CosAAException):
    def __init__(self, reason: str):
        super().__init__(
            f"Failed to parse CoT response: {reason}",
            code="COT_PARSE_FAILED",
        )


# --- Tool ---


class ToolExecutionError(CosAAException):
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            f"Tool '{tool_name}' execution failed: {reason}",
            code="TOOL_EXEC_FAILED",
        )


class ToolValidationError(CosAAException):
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            f"Tool '{tool_name}' input validation failed: {reason}",
            code="TOOL_VALIDATION_FAILED",
        )
