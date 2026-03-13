/** Shared TypeScript types matching the backend Pydantic schemas. */

export interface Session {
  session_id: string;
  tenant_id: string;
  status: string;
  goal?: string;
  created_at: string;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}

export interface Message {
  message_id: string;
  session_id: string;
  role: string;
  content: unknown;
  created_at: string;
}

export interface CycleResult {
  cycle_number: number;
  goal_achieved: boolean;
  evidence: string;
  phase: string;
  duration_ms: number;
}

export interface AgentType {
  definition_id: string;
  agent_type_name: string;
  purpose: string;
  status: string;
  created_at: string | null;
}

export interface AgentListResponse {
  agent_types: AgentType[];
  total: number;
}

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

export interface OODAProgress {
  phase: string;
  session_id: string;
  extra?: Record<string, unknown>;
}
