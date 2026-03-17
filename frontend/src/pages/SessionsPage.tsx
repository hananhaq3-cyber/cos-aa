/**
 * Session history page — list OODA sessions, filter by status, click to load.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Clock, Search, MessageSquare, Download } from "lucide-react";
import { listSessions, exportSession } from "../api/endpoints";
import clsx from "clsx";

export default function SessionsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["sessions-list", search, statusFilter],
    queryFn: () => listSessions(statusFilter ?? undefined, search || undefined),
    refetchInterval: 15_000,
  });

  const sessions = data?.sessions ?? [];

  const handleExport = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setExportingId(sessionId);
    try {
      await exportSession(sessionId, "csv");
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExportingId(null);
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Session History</h1>
        <p className="text-sm text-gray-500">
          {data?.total ?? 0} sessions
        </p>
      </div>

      {/* Search + Filter */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
        <div className="relative flex-1 w-full">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sessions..."
            className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {["All", "active", "completed", "failed"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s === "All" ? null : s)}
              className={clsx(
                "px-3 py-1.5 text-xs rounded-lg transition-colors",
                (s === "All" && !statusFilter) || statusFilter === s
                  ? "bg-primary-600/20 text-primary-400"
                  : "text-gray-400 hover:bg-gray-800"
              )}
            >
              {s === "All" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Session list */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500 text-sm">
          Loading sessions...
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12">
          <Clock size={40} className="mx-auto text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">
            No sessions found. Start a new chat to create one.
          </p>
          <button
            onClick={() => navigate("/chat")}
            className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-sm rounded-lg transition-colors"
          >
            Start Chat
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <button
              key={session.session_id}
              onClick={() => navigate("/chat")}
              className="w-full flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-colors text-left"
            >
              <div className="p-2 bg-primary-600/20 rounded-lg">
                <Clock size={18} className="text-primary-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200 truncate">
                  {session.goal || `Session ${session.session_id.slice(0, 8)}...`}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {new Date(session.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <MessageSquare size={12} />
                  {session.message_count}
                </span>
                <span
                  className={clsx(
                    "text-xs px-2 py-0.5 rounded-full border",
                    session.status === "active"
                      ? "bg-green-500/20 text-green-400 border-green-500/30"
                      : session.status === "completed"
                        ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                        : "bg-gray-500/20 text-gray-400 border-gray-500/30"
                  )}
                >
                  {session.status}
                </span>
                <button
                  onClick={(e) => handleExport(e, session.session_id)}
                  disabled={exportingId === session.session_id}
                  className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Export session as CSV"
                >
                  <Download size={16} />
                </button>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
