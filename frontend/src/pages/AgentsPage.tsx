/**
 * Agents dashboard — list registered agent types, spawn new ones.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { listAgents, spawnAgent } from "../api/endpoints";
import AgentCard from "../components/AgentCard";

const STATUS_FILTERS = ["All", "VALIDATING", "ACTIVE", "REJECTED"] as const;

export default function AgentsPage() {
  const queryClient = useQueryClient();
  const [showSpawnForm, setShowSpawnForm] = useState(false);
  const [gapDescription, setGapDescription] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("All");

  const { data, isLoading } = useQuery({
    queryKey: ["agents", statusFilter],
    queryFn: () =>
      listAgents(statusFilter === "All" ? undefined : statusFilter),
    refetchInterval: 10_000,
  });

  const spawnMutation = useMutation({
    mutationFn: (desc: string) => spawnAgent(desc, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      setShowSpawnForm(false);
      setGapDescription("");
    },
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">Agent Dashboard</h1>
          <p className="text-sm text-gray-500">
            {data?.total ?? 0} registered agent types
          </p>
        </div>
        <button
          onClick={() => setShowSpawnForm(!showSpawnForm)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-sm rounded-lg transition-colors"
        >
          <Plus size={16} /> Spawn Agent
        </button>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-6">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
              statusFilter === s
                ? "bg-primary-600/20 text-primary-400"
                : "text-gray-400 hover:bg-gray-800"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Spawn form */}
      {showSpawnForm && (
        <div className="mb-6 p-4 bg-gray-900 border border-gray-800 rounded-xl">
          <h3 className="text-sm font-medium mb-3">
            Describe the capability gap
          </h3>
          <textarea
            value={gapDescription}
            onChange={(e) => setGapDescription(e.target.value)}
            placeholder="e.g., An agent that can analyze financial reports and generate investment summaries..."
            rows={3}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500"
          />
          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={() => setShowSpawnForm(false)}
              className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200"
            >
              Cancel
            </button>
            <button
              onClick={() => spawnMutation.mutate(gapDescription)}
              disabled={!gapDescription.trim() || spawnMutation.isPending}
              className="px-4 py-1.5 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 text-sm rounded-lg transition-colors"
            >
              {spawnMutation.isPending ? "Generating..." : "Submit"}
            </button>
          </div>
          {spawnMutation.isError && (
            <p className="text-xs text-red-400 mt-2">
              Error: {(spawnMutation.error as Error).message}
            </p>
          )}
        </div>
      )}

      {/* Agent grid */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500 text-sm">
          Loading agents...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.agent_types.map((agent) => (
            <AgentCard key={agent.definition_id} agent={agent} />
          ))}
          {data?.agent_types.length === 0 && (
            <p className="col-span-full text-center py-12 text-gray-500 text-sm">
              No agents registered yet. Spawn one above.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
