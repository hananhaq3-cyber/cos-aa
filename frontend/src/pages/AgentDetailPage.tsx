/**
 * Agent detail page — shows full definition, config, and actions.
 */
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  Check,
  X,
  Wrench,
  Brain,
  Cpu,
  Clock,
} from "lucide-react";
import { getAgentDetail, approveAgent, rejectAgent } from "../api/endpoints";
import clsx from "clsx";

const statusColors: Record<string, string> = {
  ACTIVE: "bg-green-500/20 text-green-400 border-green-500/30",
  DRAFT: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  VALIDATING: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  DEPRECATED: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  FAILED: "bg-red-500/20 text-red-400 border-red-500/30",
  REJECTED: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function AgentDetailPage() {
  const { definitionId } = useParams<{ definitionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: agent, isLoading, isError } = useQuery({
    queryKey: ["agent-detail", definitionId],
    queryFn: () => getAgentDetail(definitionId!),
    enabled: !!definitionId,
  });

  const approveMutation = useMutation({
    mutationFn: () => approveAgent(definitionId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-detail", definitionId] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectAgent(definitionId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-detail", definitionId] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 text-center py-16 text-gray-500 text-sm">
        Loading agent...
      </div>
    );
  }

  if (isError || !agent) {
    return (
      <div className="p-4 sm:p-6">
        <button
          onClick={() => navigate("/agents")}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 mb-6"
        >
          <ArrowLeft size={16} /> Back to Agents
        </button>
        <p className="text-center py-16 text-red-400 text-sm">
          Agent not found.
        </p>
      </div>
    );
  }

  const colorClass =
    statusColors[agent.status] ||
    "bg-gray-500/20 text-gray-400 border-gray-500/30";

  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      {/* Back button */}
      <button
        onClick={() => navigate("/agents")}
        className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 mb-6"
      >
        <ArrowLeft size={16} /> Back to Agents
      </button>

      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <div className="p-3 bg-primary-600/20 rounded-xl">
          <Bot size={28} className="text-primary-400" />
        </div>
        <div className="flex-1">
          <h1 className="text-lg font-semibold">{agent.agent_type_name}</h1>
          <p className="text-sm text-gray-400 mt-1">{agent.purpose}</p>
          <div className="flex items-center gap-3 mt-2">
            <span
              className={clsx(
                "text-xs px-2.5 py-0.5 rounded-full border",
                colorClass
              )}
            >
              {agent.status}
            </span>
            <span className="text-xs text-gray-500">
              ID: {agent.definition_id.slice(0, 12)}...
            </span>
            {agent.created_at && (
              <span className="text-xs text-gray-500">
                Created {new Date(agent.created_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Approve/Reject actions */}
      {agent.status === "VALIDATING" && (
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-sm transition-colors"
          >
            <Check size={16} />
            {approveMutation.isPending ? "Approving..." : "Approve & Deploy"}
          </button>
          <button
            onClick={() => rejectMutation.mutate()}
            disabled={rejectMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded-lg text-sm transition-colors"
          >
            <X size={16} />
            {rejectMutation.isPending ? "Rejecting..." : "Reject"}
          </button>
        </div>
      )}

      {/* Detail sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* System Prompt */}
        <Section title="System Prompt" icon={Cpu} span={2}>
          <pre className="text-xs text-gray-300 whitespace-pre-wrap bg-gray-950 p-3 rounded-lg max-h-48 overflow-y-auto">
            {agent.system_prompt || "(no system prompt)"}
          </pre>
        </Section>

        {/* Tools */}
        <Section title="Tools" icon={Wrench}>
          {agent.tools.length === 0 ? (
            <p className="text-xs text-gray-500">No tools configured</p>
          ) : (
            <div className="space-y-2">
              {agent.tools.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 text-xs bg-gray-950 px-3 py-2 rounded-lg"
                >
                  <Wrench size={12} className="text-gray-500" />
                  <span className="text-gray-300">{t.tool_name}</span>
                  <span className="text-gray-600">({t.tool_type})</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Memory Access */}
        <Section title="Memory Access" icon={Brain}>
          <div className="space-y-1.5">
            <AccessRow label="Read Semantic" value={agent.memory_access.can_read_semantic} />
            <AccessRow label="Write Episodic" value={agent.memory_access.can_write_episodic} />
            <AccessRow label="Read Procedural" value={agent.memory_access.can_read_procedural} />
          </div>
        </Section>

        {/* Resource Limits */}
        <Section title="Resource Limits" icon={Clock}>
          <div className="space-y-1.5 text-xs">
            <LimitRow label="Max Concurrent Tasks" value={agent.resource_limits.max_concurrent_tasks} />
            <LimitRow label="Max LLM Tokens/Task" value={agent.resource_limits.max_llm_tokens_per_task.toLocaleString()} />
            <LimitRow label="Max Tool Calls/Task" value={agent.resource_limits.max_tool_calls_per_task} />
            <LimitRow label="Timeout" value={`${agent.resource_limits.timeout_seconds}s`} />
          </div>
        </Section>

        {/* Trigger Conditions */}
        <Section title="Trigger Conditions" icon={Bot}>
          {agent.trigger_conditions.length === 0 ? (
            <p className="text-xs text-gray-500">No trigger conditions</p>
          ) : (
            <ul className="list-disc list-inside text-xs text-gray-300 space-y-1">
              {agent.trigger_conditions.map((cond, i) => (
                <li key={i}>{cond}</li>
              ))}
            </ul>
          )}
        </Section>

        {/* Metadata */}
        <Section title="Metadata" icon={Cpu}>
          <div className="space-y-1.5 text-xs">
            <LimitRow label="Created By" value={agent.created_by || "SYSTEM_AUTO"} />
            <LimitRow label="Model Override" value={agent.model_override || "default"} />
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  icon: Icon,
  span,
  children,
}: {
  title: string;
  icon: React.ElementType;
  span?: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className={clsx(
        "bg-gray-900 border border-gray-800 rounded-xl p-4",
        span === 2 && "md:col-span-2"
      )}
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon size={14} className="text-gray-400" />
        <h3 className="text-sm font-medium text-gray-300">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function AccessRow({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-400">{label}</span>
      <span className={value ? "text-green-400" : "text-red-400"}>
        {value ? "Enabled" : "Disabled"}
      </span>
    </div>
  );
}

function LimitRow({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-300">{value}</span>
    </div>
  );
}
