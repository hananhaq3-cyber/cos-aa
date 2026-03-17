/**
 * Traces page — browse recent traces + search by ID for CoT audit logs.
 */
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, ChevronDown, ChevronRight, Activity, Download } from "lucide-react";
import { listTraces, getTrace, exportTrace } from "../api/endpoints";
import type { TraceResponse, TraceEntry } from "../types";
import clsx from "clsx";

const phaseColors: Record<string, string> = {
  ORIENTING: "bg-purple-500/20 text-purple-400",
  DECIDING: "bg-blue-500/20 text-blue-400",
  ACTING: "bg-yellow-500/20 text-yellow-400",
  REVIEWING: "bg-green-500/20 text-green-400",
};

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
            phaseColors[entry.phase] || "bg-gray-700 text-gray-400"
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
  const [exportingId, setExportingId] = useState<string | null>(null);

  const recentQuery = useQuery({
    queryKey: ["recent-traces"],
    queryFn: listTraces,
    refetchInterval: 30_000,
  });

  const traceMutation = useMutation({
    mutationFn: (id: string) => getTrace(id),
    onSuccess: (data) => setTraceData(data),
  });

  const handleViewSession = (sessionId: string) => {
    setTraceId(sessionId);
    traceMutation.mutate(sessionId);
  };

  const handleExport = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setExportingId(sessionId);
    try {
      await exportTrace(sessionId, "csv");
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExportingId(null);
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold mb-1">OODA Trace Viewer</h1>
        <p className="text-sm text-gray-500">
          Inspect Chain-of-Thought audit trails for any session.
        </p>
      </div>

      {/* Search by trace ID */}
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
          placeholder="Enter session / trace ID (UUID)..."
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

      {/* Active trace detail */}
      {traceMutation.isPending && (
        <p className="text-center py-8 text-gray-500 text-sm">
          Loading trace...
        </p>
      )}
      {traceMutation.isError && (
        <p className="text-center py-4 text-red-400 text-sm">
          Trace not found or error fetching data.
        </p>
      )}
      {traceData && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-400">
              {traceData.total} entries in trace{" "}
              {traceData.trace_id.slice(0, 12)}...
            </p>
            <div className="flex gap-2">
              <button
                onClick={async (e) => {
                  e.preventDefault();
                  setExportingId(traceData.trace_id);
                  try {
                    await exportTrace(traceData.trace_id, "csv");
                  } catch (err) {
                    console.error("Export failed:", err);
                  } finally {
                    setExportingId(null);
                  }
                }}
                disabled={exportingId === traceData.trace_id}
                className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Export trace as CSV"
              >
                <Download size={16} />
              </button>
              <button
                onClick={() => setTraceData(null)}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                Clear
              </button>
            </div>
          </div>
          <div className="space-y-2">
            {traceData.entries.map((entry) => (
              <TraceEntryRow key={entry.id} entry={entry} />
            ))}
          </div>
        </div>
      )}

      {/* Recent traces list */}
      {!traceData && (
        <div>
          <h2 className="text-sm font-medium text-gray-400 mb-4">
            Recent Traces ({recentQuery.data?.total ?? 0})
          </h2>
          {recentQuery.isLoading ? (
            <p className="text-center py-8 text-gray-500 text-sm">
              Loading recent traces...
            </p>
          ) : recentQuery.data && recentQuery.data.traces.length > 0 ? (
            <div className="space-y-2">
              {recentQuery.data.traces.map((trace) => (
                <button
                  key={trace.session_id}
                  onClick={() => handleViewSession(trace.session_id)}
                  className="w-full flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-colors text-left"
                >
                  <div className="p-2 bg-primary-600/20 rounded-lg">
                    <Activity size={18} className="text-primary-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-200">
                      Session {trace.session_id.slice(0, 12)}...
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {new Date(trace.first_at).toLocaleString()} &mdash;{" "}
                      {new Date(trace.last_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">
                      {trace.entry_count} entries
                    </span>
                    <div className="flex gap-1">
                      {trace.phases.map((phase) => (
                        <span
                          key={phase}
                          className={clsx(
                            "text-[10px] px-1.5 py-0.5 rounded",
                            phaseColors[phase] || "bg-gray-700 text-gray-400"
                          )}
                        >
                          {phase.slice(0, 3)}
                        </span>
                      ))}
                    </div>
                    <button
                      onClick={(e) => handleExport(e, trace.session_id)}
                      disabled={exportingId === trace.session_id}
                      className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Export trace as CSV"
                    >
                      <Download size={16} />
                    </button>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Activity size={40} className="mx-auto text-gray-700 mb-3" />
              <p className="text-sm text-gray-500">
                No traces yet. Run an OODA cycle to generate trace data.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
