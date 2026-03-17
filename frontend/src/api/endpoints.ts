/**
 * API service functions for all backend endpoints.
 */
import api from "./client";
import type {
  AgentDetail,
  AgentListResponse,
  CycleResult,
  MemoryFragment,
  MemorySearchResponse,
  Message,
  Session,
  SessionListResponse,
  TraceResponse,
} from "../types";

// ── Sessions ──

export async function listSessions(
  status?: string,
  search?: string
): Promise<SessionListResponse> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  if (search) params.search = search;
  const { data } = await api.get("/sessions", { params });
  return data;
}

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

export async function confirmSession(
  sessionId: string,
  decision: "approved" | "rejected"
): Promise<CycleResult> {
  const { data } = await api.post(`/sessions/${sessionId}/confirm`, {
    approved: decision === "approved",
  });
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

export async function getAgentDetail(definitionId: string): Promise<AgentDetail> {
  const { data } = await api.get(`/agents/${definitionId}`);
  return data;
}

export async function getAgentStats(): Promise<{
  total: number;
  by_status: Record<string, number>;
}> {
  const { data } = await api.get("/agents/stats");
  return data;
}

// ── Memory ──

export async function searchMemory(
  query: string,
  topK = 5,
  tiers = ["semantic", "episodic"],
  tags: string[] = [],
  filters?: {
    event_types?: string[];
    created_after?: string;
    created_before?: string;
    sort_by?: string;
  }
): Promise<MemorySearchResponse> {
  const { data } = await api.post("/memory/search", {
    query,
    top_k: topK,
    tiers,
    tags,
    event_types: filters?.event_types || [],
    created_after: filters?.created_after,
    created_before: filters?.created_before,
    sort_by: filters?.sort_by || "relevance",
  });
  return data;
}

export async function listMemory(
  limit = 50,
  offset = 0,
  eventType?: string
): Promise<{ memories: MemoryFragment[]; total: number }> {
  const params: Record<string, string | number> = { limit, offset };
  if (eventType) params.event_type = eventType;
  const { data } = await api.get("/memory", { params });
  return data;
}

export async function storeMemory(body: {
  content: string;
  event_type?: string;
  tags?: string[];
  importance_score?: number;
}): Promise<MemoryFragment> {
  const { data } = await api.post("/memory", body);
  return data;
}

export async function deleteMemory(fragmentId: string): Promise<void> {
  await api.delete(`/memory/${fragmentId}`);
}

export async function getMemoryStats(): Promise<{
  total: number;
  by_tier: Record<string, number>;
}> {
  const { data } = await api.get("/memory/stats");
  return data;
}

// ── Observability ──

export async function listTraces(): Promise<{
  traces: { session_id: string; entry_count: number; first_at: string; last_at: string; phases: string[] }[];
  total: number;
}> {
  const { data } = await api.get("/observability/traces");
  return data;
}

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

// ── Admin ──

export async function getAdminQuotas(): Promise<{
  quotas: { resource: string; used: number; limit: number }[];
}> {
  const { data } = await api.get("/admin/quotas");
  return data;
}

export async function getAdminKeys(): Promise<{
  keys: { key_id: string; masked_key: string; created_at: string }[];
}> {
  const { data } = await api.get("/admin/keys");
  return data;
}

export async function generateAdminKey(): Promise<{
  key_id: string;
  raw_key: string;
  created_at: string;
}> {
  const { data } = await api.post("/admin/keys");
  return data;
}

export async function revokeAdminKey(keyId: string): Promise<void> {
  await api.delete(`/admin/keys/${keyId}`);
}

export async function getAdminUsers(): Promise<{
  users: { user_id: string; email: string; role: string; created_at: string }[];
  total: number;
}> {
  const { data } = await api.get("/admin/users");
  return data;
}

export async function getAdminAnalytics(period: "today" | "week" | "month" = "week"): Promise<{
  period: string;
  total_sessions: number;
  total_messages: number;
  average_messages_per_session: number;
  data_points: Array<{ timestamp: string; sessions: number; messages: number }>;
}> {
  const { data } = await api.get("/admin/analytics", { params: { period } });
  return data;
}

// ── Export ──

export async function exportSession(
  sessionId: string,
  format: "csv" | "json" | "markdown" = "json"
): Promise<{ data: string; filename: string }> {
  const { data } = await api.get(`/sessions/${sessionId}/export`, {
    params: { format },
  });
  downloadFile(data.data, data.filename);
  return data;
}

export async function exportMemory(
  format: "csv" | "json" = "json"
): Promise<{ data: string; filename: string }> {
  const { data } = await api.get("/memory/export", {
    params: { format },
  });
  downloadFile(data.data, data.filename);
  return data;
}

export async function exportTrace(
  traceId: string,
  format: "csv" | "markdown" = "csv"
): Promise<{ data: string; filename: string }> {
  const { data } = await api.get(`/observability/traces/${traceId}/export`, {
    params: { format },
  });
  downloadFile(data.data, data.filename);
  return data;
}

// Helper to download files
function downloadFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
