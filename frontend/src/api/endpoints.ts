/**
 * API service functions for all backend endpoints.
 */
import api from "./client";
import type {
  AgentListResponse,
  CycleResult,
  MemorySearchResponse,
  Message,
  Session,
  TraceResponse,
} from "../types";

// ── Sessions ──

export async function createSession(goal: string): Promise<Session> {
  const { data } = await api.post("/sessions", { goal });
  return data;
}

export async function sendMessage(
  sessionId: string,
  content: string
): Promise<CycleResult> {
  const { data } = await api.post(`/sessions/${sessionId}/messages`, {
    content,
  });
  return data;
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const { data } = await api.get(`/sessions/${sessionId}/messages`);
  return data;
}

export async function getSessionState(sessionId: string) {
  const { data } = await api.get(`/sessions/${sessionId}/state`);
  return data;
}

// ── Agents ──

export async function listAgents(
  status?: string
): Promise<AgentListResponse> {
  const params = status ? { status } : {};
  const { data } = await api.get("/agents", { params });
  return data;
}

export async function spawnAgent(
  gapDescription: string,
  requireApproval = true
) {
  const { data } = await api.post("/agents/spawn", {
    gap_description: gapDescription,
    require_approval: requireApproval,
  });
  return data;
}

export async function approveAgent(definitionId: string) {
  const { data } = await api.post(`/agents/${definitionId}/approve`);
  return data;
}

export async function rejectAgent(definitionId: string) {
  const { data } = await api.post(`/agents/${definitionId}/reject`);
  return data;
}

// ── Memory ──

export async function searchMemory(
  query: string,
  topK = 5,
  tiers = ["semantic", "episodic"]
): Promise<MemorySearchResponse> {
  const { data } = await api.post("/memory/search", {
    query,
    top_k: topK,
    tiers,
  });
  return data;
}

// ── Observability ──

export async function getTrace(traceId: string): Promise<TraceResponse> {
  const { data } = await api.get(`/observability/traces/${traceId}`);
  return data;
}

export async function healthCheck(): Promise<{
  healthy: boolean;
  checks: Record<string, boolean>;
}> {
  const { data } = await api.get("/observability/health");
  return data;
}
