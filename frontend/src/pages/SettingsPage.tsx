/**
 * Settings page — tenant configuration, API key management, system health.
 */
import { useQuery } from "@tanstack/react-query";
import { Shield, Key, Activity } from "lucide-react";
import { healthCheck } from "../api/endpoints";
import clsx from "clsx";

export default function SettingsPage() {
  const { data: health, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: healthCheck,
    refetchInterval: 15_000,
  });

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-lg font-semibold mb-6">Settings</h1>

      {/* System Health */}
      <section className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-gray-400" />
          <h2 className="text-sm font-medium">System Health</h2>
        </div>
        {isLoading ? (
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
            Manage your tenant API keys for programmatic access.
          </p>
          <button className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-sm rounded-lg transition-colors">
            Generate New Key
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
            <span className="text-sm text-gray-400">
              JWT Token Expiry
            </span>
            <span className="text-sm text-gray-300">60 minutes</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">
              Rate Limit
            </span>
            <span className="text-sm text-gray-300">100 req/min</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">
              Tenant Isolation
            </span>
            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
              PostgreSQL RLS Active
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
