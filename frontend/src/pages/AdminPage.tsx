/**
 * Tenant Admin Panel — API Keys, Quotas, Users, Analytics.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Key, BarChart3, Users, Plus, Trash2, Copy, Check, TrendingUp } from "lucide-react";
import {
  getAdminKeys,
  generateAdminKey,
  revokeAdminKey,
  getAdminQuotas,
  getAdminUsers,
  getAdminAnalytics,
} from "../api/endpoints";
import clsx from "clsx";

type Tab = "keys" | "quotas" | "users" | "analytics";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("analytics");

  const tabs: { id: Tab; label: string; icon: typeof Key }[] = [
    { id: "analytics", label: "Analytics", icon: TrendingUp },
    { id: "keys", label: "API Keys", icon: Key },
    { id: "quotas", label: "Quotas", icon: BarChart3 },
    { id: "users", label: "Users", icon: Users },
  ];

  return (
    <div className="p-4 sm:p-6">
      <h1 className="text-lg font-semibold mb-6">Tenant Administration</h1>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 mb-6 border-b border-gray-800 pb-1">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 text-sm rounded-t-lg transition-colors",
              activeTab === id
                ? "bg-gray-900 text-primary-400 border-b-2 border-primary-500"
                : "text-gray-400 hover:text-gray-200"
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {activeTab === "analytics" && <AnalyticsTab />}
      {activeTab === "keys" && <ApiKeysTab />}
      {activeTab === "quotas" && <QuotasTab />}
      {activeTab === "users" && <UsersTab />}
    </div>
  );
}

function ApiKeysTab() {
  const queryClient = useQueryClient();
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "keys"],
    queryFn: getAdminKeys,
  });

  const generateMutation = useMutation({
    mutationFn: generateAdminKey,
    onSuccess: (res) => {
      setNewKey(res.raw_key);
      queryClient.invalidateQueries({ queryKey: ["admin", "keys"] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: revokeAdminKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "keys"] });
    },
  });

  const handleCopy = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const keys = data?.keys ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-400">{keys.length} API keys</p>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 text-sm rounded-lg transition-colors"
        >
          <Plus size={14} />
          {generateMutation.isPending ? "Generating..." : "Generate Key"}
        </button>
      </div>

      {/* Newly generated key banner */}
      {newKey && (
        <div className="p-4 bg-green-900/20 border border-green-500/30 rounded-xl">
          <p className="text-xs text-green-400 mb-2">
            Key generated! Copy it now — it won't be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-sm text-green-300 font-mono bg-gray-950 px-3 py-2 rounded-lg truncate">
              {newKey}
            </code>
            <button
              onClick={handleCopy}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              {copied ? (
                <Check size={16} className="text-green-400" />
              ) : (
                <Copy size={16} />
              )}
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : keys.length > 0 ? (
        <div className="space-y-2">
          {keys.map((key) => (
            <div
              key={key.key_id}
              className="flex items-center justify-between p-3 bg-gray-900 border border-gray-800 rounded-lg"
            >
              <div>
                <code className="text-sm text-gray-300 font-mono">
                  {key.masked_key}
                </code>
                <p className="text-xs text-gray-500 mt-1">
                  Created {new Date(key.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => revokeMutation.mutate(key.key_id)}
                disabled={revokeMutation.isPending}
                className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <Key size={36} className="mx-auto text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">
            No API keys yet. Generate one for programmatic access.
          </p>
        </div>
      )}
    </div>
  );
}

function QuotasTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "quotas"],
    queryFn: getAdminQuotas,
  });

  const quotas = data?.quotas ?? [];

  return (
    <div className="space-y-4">
      {isLoading ? (
        <p className="text-sm text-gray-500">Loading quotas...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quotas.map((q) => {
            const pct =
              q.limit > 0
                ? Math.min(100, Math.round((q.used / q.limit) * 100))
                : 0;
            return (
              <div
                key={q.resource}
                className="p-4 bg-gray-900 border border-gray-800 rounded-xl"
              >
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-gray-300">{q.resource}</span>
                  <span className="text-xs text-gray-500">
                    {q.used.toLocaleString()} / {q.limit.toLocaleString()}
                  </span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      "h-full rounded-full transition-all",
                      pct > 90
                        ? "bg-red-500"
                        : pct > 70
                          ? "bg-yellow-500"
                          : "bg-primary-500"
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AnalyticsTab() {
  const [period, setPeriod] = useState<"today" | "week" | "month">("week");
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "analytics", period],
    queryFn: () => getAdminAnalytics(period),
  });

  const analytics = data;

  return (
    <div className="space-y-6">
      {/* Period selector */}
      <div className="flex gap-2">
        {(["today", "week", "month"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={clsx(
              "px-4 py-2 text-sm rounded-lg transition-colors",
              period === p
                ? "bg-primary-600 text-white"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            )}
          >
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>

      {/* Stats cards */}
      {!isLoading && analytics && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Total Sessions</p>
            <p className="text-2xl font-bold">{analytics.total_sessions}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Total Messages</p>
            <p className="text-2xl font-bold">{analytics.total_messages}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-400 mb-1">Avg Msgs/Session</p>
            <p className="text-2xl font-bold">{analytics.average_messages_per_session}</p>
          </div>
        </div>
      )}

      {/* Activity data (simple table) */}
      {!isLoading && analytics && analytics.data_points.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-400">Time</th>
                  <th className="px-4 py-2 text-right text-gray-400">Sessions</th>
                  <th className="px-4 py-2 text-right text-gray-400">Messages</th>
                </tr>
              </thead>
              <tbody>
                {analytics.data_points.map((point, idx) => (
                  <tr key={idx} className="border-t border-gray-800">
                    <td className="px-4 py-2 text-gray-300">
                      {new Date(point.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-300">
                      {point.sessions}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-300">
                      {point.messages}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {isLoading && (
        <p className="text-center text-gray-500 py-8">Loading analytics...</p>
      )}
    </div>
  );
}

function UsersTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: getAdminUsers,
  });

  const users = data?.users ?? [];

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-400">
        {data?.total ?? 0} users in tenant
      </p>
      {isLoading ? (
        <p className="text-sm text-gray-500">Loading users...</p>
      ) : users.length > 0 ? (
        <div className="space-y-2">
          {users.map((u) => (
            <div
              key={u.user_id}
              className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl"
            >
              <div className="w-9 h-9 rounded-full bg-primary-600/20 flex items-center justify-center text-sm font-medium text-primary-400">
                {u.email[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{u.email}</p>
                <p className="text-xs text-gray-500">
                  Joined {new Date(u.created_at).toLocaleDateString()}
                </p>
              </div>
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full border",
                  u.role === "admin"
                    ? "bg-purple-500/20 text-purple-400 border-purple-500/30"
                    : u.role === "operator"
                      ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                      : "bg-gray-500/20 text-gray-400 border-gray-500/30"
                )}
              >
                {u.role}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Users size={40} className="mx-auto text-gray-700 mb-3" />
          <p className="text-sm text-gray-500">No users found.</p>
        </div>
      )}
    </div>
  );
}
