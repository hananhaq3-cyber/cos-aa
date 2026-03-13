/**
 * Traces page — view CoT audit logs and OODA trace chains.
 */
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, ChevronDown, ChevronRight } from "lucide-react";
import { getTrace } from "../api/endpoints";
import type { TraceResponse, TraceEntry } from "../types";
import clsx from "clsx";

function TraceEntryRow({ entry }: { entry: TraceEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-900/50 transition-colors"
      >
        {expanded ? (
          <ChevronDown size={14} className="text-gray-500" />
        ) : (
          <ChevronRight size={14} className="text-gray-500" />
        )}
        <span
          className={clsx(
            "text-xs font-medium px-2 py-0.5 rounded",
            entry.phase === "ORIENTING" && "bg-purple-500/20 text-purple-400",
            entry.phase === "DECIDING" && "bg-blue-500/20 text-blue-400",
            entry.phase === "ACTING" && "bg-yellow-500/20 text-yellow-400",
            entry.phase === "REVIEWING" && "bg-green-500/20 text-green-400",
            !["ORIENTING", "DECIDING", "ACTING", "REVIEWING"].includes(
              entry.phase
            ) && "bg-gray-700 text-gray-400"
          )}
        >
          {entry.phase}
        </span>
        <span className="text-sm text-gray-300 flex-1">
          Cycle: {entry.cycle_id.slice(0, 8)}...
        </span>
        <span className="text-xs text-gray-500">
          {new Date(entry.created_at).toLocaleTimeString()}
        </span>
      </button>
      {expanded && (
        <div className="px-4 py-3 bg-gray-900/30 border-t border-gray-800">
          <pre className="text-xs text-gray-400 overflow-x-auto whitespace-pre-wrap">
            {typeof entry.cot_chain === "string"
              ? entry.cot_chain
              : JSON.stringify(entry.cot_chain, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function TracesPage() {
  const [traceId, setTraceId] = useState("");
  const [traceData, setTraceData] = useState<TraceResponse | null>(null);

  const traceMutation = useMutation({
    mutationFn: (id: string) => getTrace(id),
    onSuccess: (data) => setTraceData(data),
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold mb-1">OODA Trace Viewer</h1>
        <p className="text-sm text-gray-500">
          Inspect Chain-of-Thought audit trails for any trace.
        </p>
      </div>

      {/* Search */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (traceId.trim()) traceMutation.mutate(traceId.trim());
        }}
        className="flex gap-3 mb-6"
      >
        <input
          type="text"
          value={traceId}
          onChange={(e) => setTraceId(e.target.value)}
          placeholder="Enter trace ID (UUID)..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500"
        />
        <button
          type="submit"
          disabled={traceMutation.isPending}
          className="p-3 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 rounded-xl transition-colors"
        >
          <Search size={18} />
        </button>
      </form>

      {traceMutation.isPending && (
        <p className="text-center py-8 text-gray-500 text-sm">
          Loading trace...
        </p>
      )}

      {traceMutation.isError && (
        <p className="text-center py-8 text-red-400 text-sm">
          Trace not found or error fetching data.
        </p>
      )}

      {traceData && (
        <div>
          <p className="text-sm text-gray-400 mb-4">
            {traceData.total} entries in trace {traceData.trace_id.slice(0, 12)}
            ...
          </p>
          <div className="space-y-2">
            {traceData.entries.map((entry) => (
              <TraceEntryRow key={entry.id} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
