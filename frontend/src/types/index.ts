/**
 * Shared TypeScript types matching backend Pydantic response schemas.
 */

// ── Sessions ──

export interface Session {
  session_id: string;
  tenant_id: string;
  status: string;
  created_at: string;
  goal?: string;
  message_count?: number;
}

export interface CycleResult {
  cycle_number: number;
  goal_achieved: boolean;
  evidence: string;
  phase: string;
  duration_ms: number;
  pending_confirmation?: boolean;
  proposed_action?: string;
}

export interface Message {
  message_id: string;
  session_id: string;
  role: string;
  content: string | Record<string, unknown>;
  created_at: string;
}

// ── Agents ──

export interface AgentType {
  definition_id: string;
  agent_type_name: string;
  purpose: string;
  status: string;
  created_at: string | null;
}

export interface AgentDetail {
  definition_id: string;
  agent_type_name: string;
  purpose: string;
  status: string;
  system_prompt: string;
  model_override: string | null;
  trigger_conditions: string[];
  tools: { tool_name: string; tool_type: string; config: Record<string, unknown>; permissions_required: string[] }[];
  memory_access: { can_read_semantic: boolean; can_write_episodic: boolean; can_read_procedural: boolean };
  resource_limits: { max_concurrent_tasks: number; max_llm_tokens_per_task: number; max_tool_calls_per_task: number; timeout_seconds: number };
  created_by: string;
  created_at: string | null;
}

export interface AgentListResponse {
  agent_types: AgentType[];
  total: number;
}

// ── Memory ──

export interface MemoryFragment {
  fragment_id: string;
  tier: string;
  content: string;
  summary: string;
  relevance_score: number;
  source_type: string;
  created_at: string | null;
  tags: string[];
}

export interface MemorySearchResponse {
  query: string;
  results: MemoryFragment[];
  total: number;
  retrieval_latency_ms: number;
}

export interface MemoryStats {
  total: number;
  by_tier: Record<string, number>;
}

export interface MemoryListResponse {
  memories: MemoryFragment[];
  total: number;
}

// ── Dashboard ──

export interface DashboardStats {
  agents: { total: number; by_status: Record<string, number> };
  memory: { total: number; by_tier: Record<string, number> };
  health: { healthy: boolean; checks: Record<string, boolean> };
}

// ── Observability ──

export interface TraceEntry {
  id: string;
  tenant_id: string;
  session_id: string;
  cycle_id: string;
  phase: string;
  cot_chain: unknown;
  created_at: string;
}

export interface TraceResponse {
  trace_id: string;
  tenant_id: string;
  entries: TraceEntry[];
  total: number;
}

// ── WebSocket ──

export interface OODAProgress {
  phase: string;
  session_id: string;
  extra?: Record<string, unknown>;
}

// ── Session List ──

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}
