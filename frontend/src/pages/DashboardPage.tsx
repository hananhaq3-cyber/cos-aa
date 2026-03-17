/**
 * Dashboard — platform overview with stats cards, health status, and quick actions.
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  Brain,
  Heart,
  MessageSquare,
  Sparkles,
  Search,
  ArrowRight,
} from "lucide-react";
import { getStats } from "../api/dashboard";
import clsx from "clsx";

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          {label}
        </span>
        <div className={clsx("p-2 rounded-lg", color)}>
          <Icon size={16} />
        </div>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function QuickAction({
  to,
  icon: Icon,
  label,
  description,
}: {
  to: string;
  icon: React.ElementType;
  label: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-colors group"
    >
      <div className="p-2.5 bg-primary-600/20 rounded-lg">
        <Icon size={18} className="text-primary-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-gray-500">{description}</p>
      </div>
      <ArrowRight
        size={16}
        className="text-gray-600 group-hover:text-gray-400 transition-colors"
      />
    </Link>
  );
}

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getStats,
    refetchInterval: 30_000,
  });

  const agentTotal = stats?.agents.total ?? 0;
  const activeAgents =
    stats?.agents.by_status?.ACTIVE ?? stats?.agents.by_status?.active ?? 0;
  const memoryTotal = stats?.memory.total ?? 0;
  const healthy = stats?.health.healthy ?? false;
  const checks = stats?.health.checks ?? {};

  return (
    <div className="p-4 sm:p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <LayoutDashboard size={22} className="text-primary-400" />
        <div>
          <h1 className="text-lg font-semibold">Dashboard</h1>
          <p className="text-xs text-gray-500">Platform overview</p>
        </div>
      </div>

      {/* Stats Grid */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mb-8">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 animate-pulse h-28"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mb-8">
          <StatCard
            label="Agents"
            value={agentTotal}
            sub={`${activeAgents} active`}
            icon={Bot}
            color="bg-blue-500/20 text-blue-400"
          />
          <StatCard
            label="Memory"
            value={memoryTotal}
            sub={
              Object.keys(stats?.memory.by_tier ?? {}).length > 0
                ? Object.entries(stats!.memory.by_tier)
                    .map(([t, c]) => `${c} ${t}`)
                    .join(", ")
                : "No memories yet"
            }
            icon={Brain}
            color="bg-purple-500/20 text-purple-400"
          />
          <StatCard
            label="System Health"
            value={healthy ? "Healthy" : "Degraded"}
            sub={Object.entries(checks)
              .map(([k, v]) => `${k}: ${v ? "OK" : "FAIL"}`)
              .join(" · ")}
            icon={Heart}
            color={
              healthy
                ? "bg-green-500/20 text-green-400"
                : "bg-red-500/20 text-red-400"
            }
          />
        </div>
      )}

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-400 mb-3">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <QuickAction
            to="/chat"
            icon={MessageSquare}
            label="New Chat"
            description="Start an OODA reasoning cycle"
          />
          <QuickAction
            to="/agents"
            icon={Sparkles}
            label="Spawn Agent"
            description="Create a new AI agent from a gap"
          />
          <QuickAction
            to="/memory"
            icon={Search}
            label="Search Memory"
            description="Query semantic and episodic memory"
          />
        </div>
      </div>

      {/* Health Detail */}
      {stats && (
        <div>
          <h2 className="text-sm font-medium text-gray-400 mb-3">
            Service Status
          </h2>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="space-y-2">
              {Object.entries(checks).map(([name, ok]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-400 capitalize">
                    {name}
                  </span>
                  <span
                    className={clsx(
                      "text-xs px-2 py-0.5 rounded",
                      ok
                        ? "bg-green-500/20 text-green-400"
                        : "bg-red-500/20 text-red-400"
                    )}
                  >
                    {ok ? "Operational" : "Down"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
