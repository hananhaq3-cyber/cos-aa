/**
 * Session history page — list past sessions, search, click to load.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, Search } from "lucide-react";
import { useSessionStore } from "../store/sessionStore";

export default function SessionsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const { setSession } = useSessionStore();

  const { data, isLoading } = useQuery({
    queryKey: ["sessions", search, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);
      const resp = await fetch(`/api/v1/sessions?${params}`);
      return resp.json();
    },
    refetchInterval: 15_000,
  });

  const sessions = data?.sessions ?? [];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Session History</h1>
        <p className="text-sm text-gray-500">
          {data?.total ?? 0} sessions
        </p>
      </div>

      {/* Search + Filter */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1">
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
        <div className="flex gap-1">
          {["All", "active", "completed", "failed"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s === "All" ? null : s)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                (s === "All" && !statusFilter) || statusFilter === s
                  ? "bg-primary-600/20 text-primary-400"
                  : "text-gray-400 hover:bg-gray-800"
              }`}
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
        <div className="text-center py-12 text-gray-500 text-sm">
          No sessions found.
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session: any) => (
            <button
              key={session.session_id}
              onClick={() => setSession(session)}
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
                  {new Date(session.created_at).toLocaleString()} · {session.status}
                </p>
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded-full border ${
                  session.status === "active"
                    ? "bg-green-500/20 text-green-400 border-green-500/30"
                    : session.status === "completed"
                    ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                    : "bg-gray-500/20 text-gray-400 border-gray-500/30"
                }`}
              >
                {session.status}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
