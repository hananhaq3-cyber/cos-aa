/**
 * Settings page — profile info, system health, security config summary.
 */
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Shield, Key, Activity, User, Copy, Check } from "lucide-react";
import { healthCheck, generateAdminKey } from "../api/endpoints";
import { getMe } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import clsx from "clsx";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  // Fetch current user from /auth/me endpoint
  const { data: meData } = useQuery({
    queryKey: ["auth/me"],
    queryFn: getMe,
    staleTime: 5 * 60 * 1000,  // 5 minutes
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: healthCheck,
    refetchInterval: 15_000,
  });

  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const keyMutation = useMutation({
    mutationFn: generateAdminKey,
    onSuccess: (res) => setNewKey(res.raw_key),
  });

  const handleCopy = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-3xl">
      <h1 className="text-lg font-semibold mb-6">Settings</h1>

      {/* Profile */}
      <section className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <User size={18} className="text-gray-400" />
          <h2 className="text-sm font-medium">Profile</h2>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-primary-600/20 flex items-center justify-center text-lg font-semibold text-primary-400">
              {(meData?.email ?? user?.email)?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div>
              <p className="text-sm text-gray-200">{meData?.email ?? user?.email ?? "Unknown"}</p>
              <p className="text-xs text-gray-500 capitalize">{meData?.role ?? user?.role ?? "viewer"}</p>
            </div>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-gray-800">
            <span className="text-sm text-gray-400">Tenant ID</span>
            <code className="text-xs text-gray-500 font-mono">
              {(meData?.tenant_id ?? user?.tenant_id)?.slice(0, 16)}...
            </code>
          </div>
          {meData?.email_verified && (
            <div className="flex items-center justify-between pt-2 border-t border-gray-800">
              <span className="text-sm text-gray-400">Email Status</span>
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">
                ✓ Verified
              </span>
            </div>
          )}
        </div>
      </section>

      {/* System Health */}
      <section className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-gray-400" />
          <h2 className="text-sm font-medium">System Health</h2>
        </div>
        {healthLoading ? (
          <p className="text-sm text-gray-500">Checking health...</p>
        ) : health ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <div
                className={clsx(
                  "w-2.5 h-2.5 rounded-full",
                  health.healthy ? "bg-green-500" : "bg-red-500"
                )}
              />
              <span className="text-sm">
                {health.healthy ? "All systems operational" : "Degraded"}
              </span>
            </div>
            <div className="space-y-2">
              {Object.entries(health.checks).map(([name, ok]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">{name}</span>
                  <span
                    className={clsx(
                      "text-xs px-2 py-0.5 rounded",
                      ok
                        ? "bg-green-500/20 text-green-400"
                        : "bg-red-500/20 text-red-400"
                    )}
                  >
                    {ok ? "OK" : "FAIL"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {/* API Keys */}
      <section className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Key size={18} className="text-gray-400" />
          <h2 className="text-sm font-medium">API Keys</h2>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-sm text-gray-400 mb-3">
            Generate API keys for programmatic access. Manage all keys in the Admin panel.
          </p>

          {newKey && (
            <div className="mb-3 p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
              <p className="text-xs text-green-400 mb-1.5">
                Copy this key — it won't be shown again.
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs text-green-300 font-mono bg-gray-950 px-2 py-1.5 rounded truncate">
                  {newKey}
                </code>
                <button
                  onClick={handleCopy}
                  className="p-1.5 bg-gray-800 hover:bg-gray-700 rounded transition-colors"
                >
                  {copied ? (
                    <Check size={14} className="text-green-400" />
                  ) : (
                    <Copy size={14} />
                  )}
                </button>
              </div>
            </div>
          )}

          <button
            onClick={() => keyMutation.mutate()}
            disabled={keyMutation.isPending}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 text-sm rounded-lg transition-colors"
          >
            {keyMutation.isPending ? "Generating..." : "Generate New Key"}
          </button>
        </div>
      </section>

      {/* Security */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Shield size={18} className="text-gray-400" />
          <h2 className="text-sm font-medium">Security</h2>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">JWT Token Expiry</span>
            <span className="text-sm text-gray-300">60 minutes</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Token Algorithm</span>
            <span className="text-sm text-gray-300">HS256</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Password Hashing</span>
            <span className="text-sm text-gray-300">Argon2</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Rate Limit</span>
            <span className="text-sm text-gray-300">100 req/min</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Tenant Isolation</span>
            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
              PostgreSQL RLS Active
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Token Blacklist</span>
            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
              Redis TTL
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
