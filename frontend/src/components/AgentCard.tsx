/**
 * Agent card for the agents dashboard.
 */
import { useNavigate } from "react-router-dom";
import { Bot, Check, X, ChevronRight } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import type { AgentType } from "../types";
import { approveAgent, rejectAgent } from "../api/endpoints";

interface AgentCardProps {
  agent: AgentType;
}

const statusColors: Record<string, string> = {
  ACTIVE: "bg-green-500/20 text-green-400 border-green-500/30",
  DRAFT: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  VALIDATING: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  DEPRECATED: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  FAILED: "bg-red-500/20 text-red-400 border-red-500/30",
  REJECTED: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function AgentCard({ agent }: AgentCardProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const colorClass =
    statusColors[agent.status] ||
    "bg-gray-500/20 text-gray-400 border-gray-500/30";

  const approveMutation = useMutation({
    mutationFn: () => approveAgent(agent.definition_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agents"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectAgent(agent.definition_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div
      className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors cursor-pointer"
      onClick={() => navigate(`/agents/${agent.definition_id}`)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-600/20 rounded-lg">
            <Bot size={20} className="text-primary-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200">
              {agent.agent_type_name}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {agent.definition_id.slice(0, 8)}...
            </p>
          </div>
        </div>
        <span
          className={clsx(
            "text-xs px-2 py-0.5 rounded-full border",
            colorClass
          )}
        >
          {agent.status}
        </span>
      </div>
      <p className="text-sm text-gray-400 leading-relaxed">{agent.purpose}</p>
      {agent.created_at && (
        <p className="text-xs text-gray-600 mt-3">
          Created {new Date(agent.created_at).toLocaleDateString()}
        </p>
      )}
      {agent.status === "VALIDATING" && (
        <div className="flex gap-2 mt-3 pt-3 border-t border-gray-800">
          <button
            onClick={(e) => { e.stopPropagation(); approveMutation.mutate(); }}
            disabled={approveMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 text-xs rounded-lg transition-colors"
          >
            <Check size={14} />
            {approveMutation.isPending ? "..." : "Approve"}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); rejectMutation.mutate(); }}
            disabled={rejectMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 text-red-400 hover:bg-red-600/30 text-xs rounded-lg transition-colors"
          >
            <X size={14} />
            {rejectMutation.isPending ? "..." : "Reject"}
          </button>
        </div>
      )}
      <div className="flex items-center justify-end mt-3 pt-3 border-t border-gray-800">
        <span className="flex items-center gap-1 text-xs text-gray-500 hover:text-primary-400 transition-colors">
          View Details <ChevronRight size={12} />
        </span>
      </div>
    </div>
  );
}
