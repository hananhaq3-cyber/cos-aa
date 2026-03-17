/**
 * Security page — active sessions management and audit log.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Monitor, Globe, Clock, X, Shield, AlertTriangle } from "lucide-react";
import { getSessions, revokeSession, revokeAllSessions } from "../api/auth";
import type { SessionInfo } from "../types/auth";
import clsx from "clsx";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function parseUserAgent(ua: string | null): string {
  if (!ua) return "Unknown device";
  if (ua.includes("Chrome")) return "Chrome";
  if (ua.includes("Firefox")) return "Firefox";
  if (ua.includes("Safari")) return "Safari";
  if (ua.includes("Edge")) return "Edge";
  return ua.slice(0, 40);
}

function SessionCard({
  session,
  onRevoke,
  revoking,
}: {
  session: SessionInfo;
  onRevoke: (jti: string) => void;
  revoking: boolean;
}) {
  const isExpired = new Date(session.expires_at) < new Date();
  const status = session.is_current
    ? "current"
    : session.is_revoked
      ? "revoked"
      : isExpired
        ? "expired"
        : "active";

  return (
    <div
      className={clsx(
        "bg-gray-900 border rounded-xl p-4",
        session.is_current
          ? "border-primary-500/50"
          : session.is_revoked
            ? "border-red-500/30 opacity-60"
            : "border-gray-800"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Monitor size={18} className="text-gray-400 shrink-0" />
          <div>
            <p className="text-sm font-medium">
              {parseUserAgent(session.user_agent)}
              {session.is_current && (
                <span className="ml-2 text-xs bg-primary-500/20 text-primary-400 px-2 py-0.5 rounded">
                  Current
                </span>
              )}
            </p>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              {session.ip_address && (
                <span className="flex items-center gap-1">
                  <Globe size={12} />
                  {session.ip_address}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {formatDate(session.created_at)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              "text-xs px-2 py-0.5 rounded",
              status === "current" && "bg-primary-500/20 text-primary-400",
              status === "active" && "bg-green-500/20 text-green-400",
              status === "revoked" && "bg-red-500/20 text-red-400",
              status === "expired" && "bg-gray-500/20 text-gray-400"
            )}
          >
            {status}
          </span>
          {!session.is_current && !session.is_revoked && !isExpired && (
            <button
              onClick={() => onRevoke(session.jti)}
              disabled={revoking}
              className="p-1.5 rounded-lg text-gray-500 hover:bg-red-900/20 hover:text-red-400 transition-colors disabled:opacity-40"
              title="Revoke session"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SecurityPage() {
  const queryClient = useQueryClient();
  const [revokeError, setRevokeError] = useState("");

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: getSessions,
    refetchInterval: 30_000,
  });

  const revokeMutation = useMutation({
    mutationFn: revokeSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      setRevokeError("");
    },
    onError: (err: Error) => setRevokeError(err.message),
  });

  const revokeAllMutation = useMutation({
    mutationFn: revokeAllSessions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      setRevokeError("");
    },
    onError: (err: Error) => setRevokeError(err.message),
  });

  const activeSessions =
    sessions?.filter((s) => !s.is_revoked && new Date(s.expires_at) > new Date()) ?? [];

  return (
    <div className="p-4 sm:p-6 max-w-3xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-2">
          <Shield size={20} className="text-primary-400" />
          <h1 className="text-lg font-semibold">Security</h1>
        </div>
        {activeSessions.length > 1 && (
          <button
            onClick={() => revokeAllMutation.mutate()}
            disabled={revokeAllMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 text-xs bg-red-900/20 text-red-400 hover:bg-red-900/40 rounded-lg transition-colors disabled:opacity-40"
          >
            <AlertTriangle size={14} />
            {revokeAllMutation.isPending ? "Revoking..." : "Revoke All Other Sessions"}
          </button>
        )}
      </div>

      {revokeError && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-sm text-red-400">
          {revokeError}
        </div>
      )}

      {/* Active Sessions */}
      <section className="mb-8">
        <h2 className="text-sm font-medium text-gray-400 mb-3">
          Active Sessions ({activeSessions.length})
        </h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-400 border-t-transparent" />
          </div>
        ) : sessions && sessions.length > 0 ? (
          <div className="space-y-3">
            {sessions.map((session) => (
              <SessionCard
                key={session.id}
                session={session}
                onRevoke={(jti) => revokeMutation.mutate(jti)}
                revoking={revokeMutation.isPending}
              />
            ))}
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
            <p className="text-sm text-gray-500">No active sessions found.</p>
          </div>
        )}
      </section>
    </div>
  );
}
