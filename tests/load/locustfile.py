"""
COS-AA v2.0 Load Testing Suite

Tests COS-AA v2.0 load characteristics by simulating concurrent tenant
activity across the platform's core API surface. This script models a
realistic traffic mix including session management, message exchange,
memory search, and agent lifecycle operations.

Designed to be run with:
    locust -f locustfile.py --headless -u 100 -r 10 \
        --host http://localhost:8000 -t 5m

Where:
    -u 100   : 100 concurrent simulated tenants
    -r 10    : ramp up 10 users per second
    -t 5m    : run for 5 minutes
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from typing import Any

from locust import HttpUser, between, events, task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_tenant_id() -> str:
    """Generate a unique tenant identifier for the simulated user."""
    return f"tenant-{uuid.uuid4().hex[:12]}"


def _random_message_content() -> str:
    """Return a representative message payload."""
    return (
        "Analyze the current cognitive state and provide "
        "a summary of active reasoning chains."
    )


def _random_memory_query() -> str:
    """Return a representative memory-search query."""
    return "recent reasoning about decision optimization"


def _random_agent_config() -> dict[str, Any]:
    """Return a minimal agent-spawn configuration."""
    return {
        "agent_type": "reasoning",
        "name": f"agent-{uuid.uuid4().hex[:8]}",
        "config": {
            "model": "default",
            "temperature": 0.7,
            "max_tokens": 1024,
        },
    }


# ---------------------------------------------------------------------------
# Event hooks
# ---------------------------------------------------------------------------

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log when the load test begins."""
    print("[COS-AA Load Test] Starting load test against "
          f"{environment.host} ...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log summary when the load test ends."""
    print("[COS-AA Load Test] Load test complete.")


# ---------------------------------------------------------------------------
# User behaviour
# ---------------------------------------------------------------------------

class CosAATenantUser(HttpUser):
    """Simulates a single COS-AA tenant performing a realistic mix of API
    operations.

    Task weights reflect expected production traffic ratios:
        - message_send        (5) : highest frequency, chat-style interaction
        - memory_search       (3) : frequent look-ups against memory store
        - agent_list          (2) : periodic dashboard / status polling
        - agent_spawn         (1) : occasional new-agent creation
        - health_check        (1) : low-frequency liveness probe
    """

    # Wait between 1 and 5 seconds between tasks.
    wait_time = between(1, 5)

    # Attributes set during on_start.
    tenant_id: str = ""
    session_id: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_start(self) -> None:
        """Called once per simulated user.  Creates a tenant session that is
        reused for subsequent requests."""
        self.tenant_id = _random_tenant_id()
        self._create_session()

    def _create_session(self) -> None:
        """POST /api/v1/sessions -- create a new session for this tenant."""
        payload = {
            "tenant_id": self.tenant_id,
            "metadata": {
                "source": "load_test",
                "user_agent": "locust-cos-aa",
            },
        }
        with self.client.post(
            "/api/v1/sessions",
            json=payload,
            headers=self._headers(),
            name="/api/v1/sessions [create]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                    self.session_id = data.get("session_id") or data.get("id")
                    if not self.session_id:
                        response.failure(
                            "Session created but no session_id in response body"
                        )
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in session-creation response")
            else:
                response.failure(
                    f"Session creation failed with status {response.status_code}"
                )

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Return common request headers including the tenant identifier."""
        return {
            "Content-Type": "application/json",
            "X-Tenant-ID": self.tenant_id,
        }

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task(5)
    def message_send(self) -> None:
        """POST /api/v1/sessions/{session_id}/messages -- send a message and
        then GET the message list to verify it was persisted."""
        if not self.session_id:
            self._create_session()
            if not self.session_id:
                return

        # --- send message ---
        payload = {
            "content": _random_message_content(),
            "role": "user",
            "metadata": {"source": "load_test"},
        }
        with self.client.post(
            f"/api/v1/sessions/{self.session_id}/messages",
            json=payload,
            headers=self._headers(),
            name="/api/v1/sessions/{id}/messages [send]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                    if not (data.get("message_id") or data.get("id")):
                        response.failure("No message_id in send response")
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in message-send response")
            else:
                response.failure(
                    f"Message send failed with status {response.status_code}"
                )

        # --- list messages (read-back verification) ---
        with self.client.get(
            f"/api/v1/sessions/{self.session_id}/messages",
            headers=self._headers(),
            name="/api/v1/sessions/{id}/messages [list]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Accept both list and dict-with-list envelope.
                    messages = data if isinstance(data, list) else data.get("messages", [])
                    if not isinstance(messages, list):
                        response.failure("Unexpected messages payload structure")
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in message-list response")
            else:
                response.failure(
                    f"Message list failed with status {response.status_code}"
                )

    @task(3)
    def memory_search(self) -> None:
        """POST /api/v1/memory/search -- query the memory store."""
        payload = {
            "query": _random_memory_query(),
            "tenant_id": self.tenant_id,
            "top_k": 5,
        }
        with self.client.post(
            "/api/v1/memory/search",
            json=payload,
            headers=self._headers(),
            name="/api/v1/memory/search",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    results = data if isinstance(data, list) else data.get("results", [])
                    if not isinstance(results, list):
                        response.failure("Unexpected memory-search response structure")
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in memory-search response")
            else:
                response.failure(
                    f"Memory search failed with status {response.status_code}"
                )

    @task(2)
    def agent_list(self) -> None:
        """GET /api/v1/agents -- list available agents."""
        with self.client.get(
            "/api/v1/agents",
            headers=self._headers(),
            name="/api/v1/agents [list]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    agents = data if isinstance(data, list) else data.get("agents", [])
                    if not isinstance(agents, list):
                        response.failure("Unexpected agents-list response structure")
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in agent-list response")
            else:
                response.failure(
                    f"Agent list failed with status {response.status_code}"
                )

    @task(1)
    def agent_spawn(self) -> None:
        """POST /api/v1/agents/spawn -- create a new agent instance."""
        payload = _random_agent_config()
        payload["tenant_id"] = self.tenant_id

        with self.client.post(
            "/api/v1/agents/spawn",
            json=payload,
            headers=self._headers(),
            name="/api/v1/agents/spawn",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                    if not (data.get("agent_id") or data.get("id")):
                        response.failure("No agent_id in spawn response")
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in agent-spawn response")
            else:
                response.failure(
                    f"Agent spawn failed with status {response.status_code}"
                )

    @task(1)
    def health_check(self) -> None:
        """GET /api/v1/observability/health -- lightweight liveness probe."""
        with self.client.get(
            "/api/v1/observability/health",
            name="/api/v1/observability/health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    status = data.get("status", "").lower()
                    if status in ("ok", "healthy", "up"):
                        response.success()
                    else:
                        response.failure(
                            f"Health check returned unexpected status: {status}"
                        )
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in health-check response")
            else:
                response.failure(
                    f"Health check failed with status {response.status_code}"
                )


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running directly: python locustfile.py
    # Delegates to locust CLI with sensible defaults for COS-AA load testing.
    default_args = [
        "locust",
        "-f", __file__,
        "--headless",
        "-u", "100",
        "-r", "10",
        "--host", os.environ.get("COSAA_HOST", "http://localhost:8000"),
        "-t", "5m",
    ]
    print(f"[COS-AA Load Test] Launching: {' '.join(default_args)}")
    sys.exit(subprocess.call(default_args))
