"""
COS-AA Mock Backend API Server
Provides realistic responses to all frontend API calls without requiring
Postgres, Redis, or external LLM services. Simulates the full OODA cycle.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="COS-AA Mock Server", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state ──
sessions: dict[str, dict] = {}
session_messages: dict[str, list] = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
#  OODA Cycle Simulation Logic
# ═══════════════════════════════════════════════════════════════

OODA_RESPONSES = {
    "exam": {
        "evidence": (
            "4-week AI exam study plan generated successfully.\n\n"
            "**Week 1:** Machine Learning fundamentals + Neural Networks\n"
            "**Week 2:** NLP + Transformer architectures\n"
            "**Week 3:** Computer Vision + CNNs\n"
            "**Week 4:** Reinforcement Learning + Practice exams\n\n"
            "Covers 5 key AI topics with progressive difficulty. "
            "Includes practice exam recommendations for week 4."
        ),
        "phase": "COMPLETE",
        "goal_achieved": True,
    },
    "code": {
        "evidence": (
            "Code analysis and solution generated.\n\n"
            "**Approach:** Analyzed the requirements, identified optimal data structures, "
            "and generated a solution with O(n log n) time complexity.\n\n"
            "**Tools used:** code_interpreter for validation, web_search for best practices.\n"
            "**Result:** Solution verified with 15 test cases, all passing."
        ),
        "phase": "COMPLETE",
        "goal_achieved": True,
    },
    "research": {
        "evidence": (
            "Research synthesis complete.\n\n"
            "**Sources analyzed:** 12 academic papers, 5 industry reports\n"
            "**Key findings:**\n"
            "1. Transformer architectures dominate current NLP benchmarks\n"
            "2. Multimodal models show 23% improvement on cross-domain tasks\n"
            "3. Efficiency techniques (pruning, quantization) reduce compute by 40%\n\n"
            "Full report stored in semantic memory for future retrieval."
        ),
        "phase": "COMPLETE",
        "goal_achieved": True,
    },
    "default": {
        "evidence": (
            "Task completed through OODA cognitive processing.\n\n"
            "**OBSERVE:** Collected and normalized your input\n"
            "**ORIENT:** Analyzed intent via Chain-of-Thought reasoning (confidence: 0.89)\n"
            "**DECIDE:** Generated action plan with 2 steps\n"
            "**ACT:** Dispatched to Knowledge + Planning agents (both succeeded)\n"
            "**REVIEW:** Goal achieved - results verified against success criteria\n\n"
            "The response has been stored in episodic memory for future context."
        ),
        "phase": "COMPLETE",
        "goal_achieved": True,
    },
}


def get_ooda_response(content: str) -> dict:
    content_lower = content.lower()
    for key in OODA_RESPONSES:
        if key != "default" and key in content_lower:
            return OODA_RESPONSES[key]
    return OODA_RESPONSES["default"]


# ═══════════════════════════════════════════════════════════════
#  API Routes — Sessions
# ═══════════════════════════════════════════════════════════════

@app.post("/api/v1/sessions")
async def create_session(request: Request):
    body = await request.json()
    sid = new_id()
    tid = new_id()
    session = {
        "session_id": sid,
        "tenant_id": tid,
        "status": "active",
        "goal": body.get("goal", ""),
        "created_at": now_iso(),
    }
    sessions[sid] = session
    session_messages[sid] = []
    return session


@app.get("/api/v1/sessions")
async def list_sessions(search: str = "", status: str = ""):
    """List all sessions with optional search and status filtering."""
    results = list(sessions.values())
    if status:
        results = [s for s in results if s["status"] == status]
    if search:
        search_lower = search.lower()
        results = [
            s for s in results
            if search_lower in s.get("goal", "").lower()
            or search_lower in s["session_id"].lower()
        ]
    results.sort(key=lambda s: s["created_at"], reverse=True)
    return {"sessions": results, "total": len(results)}


@app.post("/api/v1/sessions/{session_id}/messages")
async def send_message(session_id: str, request: Request):
    body = await request.json()
    content = body.get("content", "")

    # Store user message
    if session_id not in session_messages:
        session_messages[session_id] = []

    session_messages[session_id].append({
        "message_id": new_id(),
        "session_id": session_id,
        "role": "USER",
        "content": content,
        "created_at": now_iso(),
    })

    # Simulate OODA cycle processing time (phased delays)
    await asyncio.sleep(0.3)  # OBSERVE
    await asyncio.sleep(0.4)  # ORIENT (CoT reasoning)
    await asyncio.sleep(0.2)  # DECIDE
    await asyncio.sleep(0.3)  # ACT (agent dispatch)
    await asyncio.sleep(0.2)  # REVIEW

    t_start = time.perf_counter()
    ooda = get_ooda_response(content)
    duration = (time.perf_counter() - t_start) * 1000 + 1400  # include simulated delays

    # Store assistant response
    session_messages[session_id].append({
        "message_id": new_id(),
        "session_id": session_id,
        "role": "ASSISTANT",
        "content": ooda["evidence"],
        "created_at": now_iso(),
    })

    return {
        "cycle_number": len([m for m in session_messages.get(session_id, []) if m["role"] == "USER"]),
        "goal_achieved": ooda["goal_achieved"],
        "evidence": ooda["evidence"],
        "phase": ooda["phase"],
        "duration_ms": round(duration, 1),
    }


@app.get("/api/v1/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    return session_messages.get(session_id, [])


@app.get("/api/v1/sessions/{session_id}/state")
async def get_session_state(session_id: str):
    return {
        "session_id": session_id,
        "phase": "IDLE",
        "iteration": 0,
        "messages_count": len(session_messages.get(session_id, [])),
    }


# ═══════════════════════════════════════════════════════════════
#  API Routes — Agents
# ═══════════════════════════════════════════════════════════════

BUILTIN_AGENTS = [
    {
        "definition_id": new_id(),
        "agent_type_name": "PLANNING",
        "purpose": "Goal decomposition, task scheduling, and workflow generation",
        "status": "ACTIVE",
        "created_at": "2026-01-15T10:00:00Z",
    },
    {
        "definition_id": new_id(),
        "agent_type_name": "KNOWLEDGE",
        "purpose": "Information retrieval, web search, and knowledge synthesis",
        "status": "ACTIVE",
        "created_at": "2026-01-15T10:00:00Z",
    },
    {
        "definition_id": new_id(),
        "agent_type_name": "LEARNING",
        "purpose": "Pattern extraction from completed cycles, procedural memory updates",
        "status": "ACTIVE",
        "created_at": "2026-01-15T10:00:00Z",
    },
    {
        "definition_id": new_id(),
        "agent_type_name": "MONITORING",
        "purpose": "Anomaly detection, system health analysis, and alert management",
        "status": "ACTIVE",
        "created_at": "2026-01-15T10:00:00Z",
    },
]

spawned_agents: list[dict] = []


@app.get("/api/v1/agents")
async def list_agents(status: str = None):
    agents = BUILTIN_AGENTS + spawned_agents
    if status:
        agents = [a for a in agents if a["status"] == status]
    return {"agent_types": agents, "total": len(agents)}


@app.post("/api/v1/agents/spawn")
async def spawn_agent(request: Request):
    body = await request.json()
    gap = body.get("gap_description", "custom task")

    # Simulate LLM generating an agent definition
    await asyncio.sleep(0.5)

    name = gap.upper().replace(" ", "_")[:30]
    agent = {
        "definition_id": new_id(),
        "agent_type_name": name,
        "purpose": f"Auto-generated agent for: {gap}",
        "status": "ACTIVE" if not body.get("require_approval", True) else "VALIDATING",
        "created_at": now_iso(),
    }
    spawned_agents.append(agent)
    return agent


@app.post("/api/v1/agents/{definition_id}/approve")
async def approve_agent(definition_id: str):
    """Approve a VALIDATING agent, transitioning it to ACTIVE."""
    for agent in spawned_agents:
        if agent["definition_id"] == definition_id:
            agent["status"] = "ACTIVE"
            return agent
    return {"error": "Agent not found"}, 404


@app.post("/api/v1/agents/{definition_id}/reject")
async def reject_agent(definition_id: str):
    """Reject a VALIDATING agent, transitioning it to REJECTED."""
    for agent in spawned_agents:
        if agent["definition_id"] == definition_id:
            agent["status"] = "REJECTED"
            return agent
    return {"error": "Agent not found"}, 404


# ═══════════════════════════════════════════════════════════════
#  API Routes — Memory
# ═══════════════════════════════════════════════════════════════

@app.post("/api/v1/memory/search")
async def search_memory(request: Request):
    body = await request.json()
    query = body.get("query", "")
    top_k = body.get("top_k", 5)

    await asyncio.sleep(0.15)  # simulate retrieval latency

    results = [
        {
            "fragment_id": new_id(),
            "tier": "SEMANTIC",
            "content": "Neural networks are computational models inspired by biological neural networks, consisting of layers of interconnected nodes.",
            "summary": "Neural networks overview",
            "relevance_score": 0.92,
            "source_type": "DOCUMENT",
            "created_at": "2026-03-01T10:00:00Z",
            "tags": ["ML", "neural_networks"],
        },
        {
            "fragment_id": new_id(),
            "tier": "EPISODIC",
            "content": f"Previous query related to '{query}' was processed successfully in session context.",
            "summary": f"Related session memory for: {query[:50]}",
            "relevance_score": 0.85,
            "source_type": "EPISODIC",
            "created_at": now_iso(),
            "tags": ["session", "query"],
        },
        {
            "fragment_id": new_id(),
            "tier": "SEMANTIC",
            "content": "Transformer architecture uses self-attention mechanisms to process sequential data in parallel, enabling significant speedups over RNNs.",
            "summary": "Transformer architecture",
            "relevance_score": 0.78,
            "source_type": "DOCUMENT",
            "created_at": "2026-02-15T10:00:00Z",
            "tags": ["transformers", "NLP", "attention"],
        },
        {
            "fragment_id": new_id(),
            "tier": "PROCEDURAL",
            "content": "Pattern: research_task -> web_search -> synthesize -> store_semantic -> report. Success rate: 94%",
            "summary": "Research task workflow pattern",
            "relevance_score": 0.71,
            "source_type": "EPISODIC",
            "created_at": "2026-02-20T10:00:00Z",
            "tags": ["workflow", "research"],
        },
    ]

    return {
        "query": query,
        "results": results[:top_k],
        "total": len(results[:top_k]),
        "retrieval_latency_ms": 42.5,
    }


# ═══════════════════════════════════════════════════════════════
#  API Routes — Observability
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/observability/health")
async def health_check():
    return {
        "healthy": True,
        "checks": {
            "postgres": True,
            "redis": True,
            "llm": True,
            "vector_store": True,
        },
    }


@app.get("/api/v1/observability/metrics")
async def metrics():
    return {"message": "Prometheus metrics endpoint (mock)"}


@app.get("/api/v1/observability/traces/{trace_id}")
async def get_trace(trace_id: str):
    sid = new_id()
    return {
        "trace_id": trace_id,
        "tenant_id": new_id(),
        "entries": [
            {
                "id": new_id(),
                "tenant_id": new_id(),
                "session_id": sid,
                "cycle_id": new_id(),
                "phase": "ORIENT",
                "cot_chain": [
                    {"step_number": 1, "step_name": "Intent Analysis",
                     "reasoning": "User is requesting information retrieval and synthesis.",
                     "confidence": 0.95},
                    {"step_number": 2, "step_name": "Agent Selection",
                     "reasoning": "Knowledge agent best suited for this task type.",
                     "confidence": 0.91},
                    {"step_number": 3, "step_name": "Plan Formation",
                     "reasoning": "Search -> Synthesize -> Verify -> Respond",
                     "confidence": 0.88},
                ],
                "created_at": now_iso(),
            },
        ],
        "total": 1,
    }


# ═══════════════════════════════════════════════════════════════
#  API Routes — Admin
# ═══════════════════════════════════════════════════════════════

mock_api_keys: list[dict] = [
    {
        "id": new_id(),
        "masked": "cos-aa_****...7f3a",
        "created_at": "2026-02-01T10:00:00Z",
    },
    {
        "id": new_id(),
        "masked": "cos-aa_****...b12e",
        "created_at": "2026-03-01T10:00:00Z",
    },
]


@app.get("/api/v1/admin/keys")
async def list_api_keys():
    return {"keys": mock_api_keys}


@app.post("/api/v1/admin/keys")
async def generate_api_key():
    key_id = new_id()
    key = {
        "id": key_id,
        "masked": f"cos-aa_****...{key_id[-4:]}",
        "created_at": now_iso(),
    }
    mock_api_keys.append(key)
    return key


@app.delete("/api/v1/admin/keys/{key_id}")
async def revoke_api_key(key_id: str):
    for i, key in enumerate(mock_api_keys):
        if key["id"] == key_id:
            mock_api_keys.pop(i)
            return {"deleted": True}
    return {"deleted": False}


@app.get("/api/v1/admin/quotas")
async def get_quotas():
    return {
        "quotas": [
            {"resource": "OODA Cycles / day", "used": 847, "limit": 5000},
            {"resource": "LLM Tokens / day", "used": 1_230_000, "limit": 5_000_000},
            {"resource": "Memory Fragments", "used": 12_450, "limit": 100_000},
            {"resource": "Agent Spawns / month", "used": 14, "limit": 50},
            {"resource": "API Requests / hour", "used": 320, "limit": 1000},
            {"resource": "Storage (MB)", "used": 256, "limit": 1024},
        ]
    }


# ═══════════════════════════════════════════════════════════════
#  Root endpoints
# ═══════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"service": "COS-AA", "version": "2.0.0", "status": "running", "mode": "mock"}


@app.get("/health")
async def health():
    return {"healthy": True, "checks": {"mock_server": True}}


if __name__ == "__main__":
    print("\n  COS-AA Mock Backend API Server")
    print("  ================================")
    print("  Listening on http://localhost:8000")
    print("  Frontend proxy target: /api/v1/* -> localhost:8000")
    print("  Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
