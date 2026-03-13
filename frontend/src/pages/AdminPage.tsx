/**
 * Tenant Admin Panel — API Keys, Quotas, Users.
 */
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Key, BarChart3, Users, Plus, Trash2 } from "lucide-react";

type Tab = "keys" | "quotas" | "users";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("keys");

  const tabs: { id: Tab; label: string; icon: typeof Key }[] = [
    { id: "keys", label: "API Keys", icon: Key },
    { id: "quotas", label: "Quotas", icon: BarChart3 },
    { id: "users", label: "Users", icon: Users },
  ];

  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold mb-6">Tenant Administration</h1>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-800 pb-1">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-t-lg transition-colors ${
              activeTab === id
                ? "bg-gray-900 text-primary-400 border-b-2 border-primary-500"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {activeTab === "keys" && <ApiKeysTab />}
      {activeTab === "quotas" && <QuotasTab />}
      {activeTab === "users" && <UsersTab />}
    </div>
  );
}

function ApiKeysTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "keys"],
    queryFn: async () => {
      const resp = await fetch("/api/v1/admin/keys");
      return resp.json();
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const resp = await fetch("/api/v1/admin/keys", { method: "POST" });
      return resp.json();
    },
  });

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

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <div className="space-y-2">
          {keys.map((key: any) => (
            <div
              key={key.id}
              className="flex items-center justify-between p-3 bg-gray-900 border border-gray-800 rounded-lg"
            >
              <div>
                <code className="text-sm text-gray-300 font-mono">
                  {key.masked}
                </code>
                <p className="text-xs text-gray-500 mt-1">
                  Created {new Date(key.created_at).toLocaleDateString()}
                </p>
              </div>
              <button className="p-1.5 text-gray-500 hover:text-red-400 transition-colors">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function QuotasTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "quotas"],
    queryFn: async () => {
      const resp = await fetch("/api/v1/admin/quotas");
      return resp.json();
    },
  });

  const quotas = data?.quotas ?? [];

  return (
    <div className="space-y-4">
      {isLoading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quotas.map((q: any) => {
            const pct = Math.min(100, Math.round((q.used / q.limit) * 100));
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
                    className={`h-full rounded-full transition-all ${
                      pct > 90
                        ? "bg-red-500"
                        : pct > 70
                        ? "bg-yellow-500"
                        : "bg-primary-500"
                    }`}
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

function UsersTab() {
  return (
    <div className="text-center py-12">
      <Users size={48} className="mx-auto text-gray-700 mb-4" />
      <p className="text-sm text-gray-500">
        User management coming soon.
      </p>
    </div>
  );
}
