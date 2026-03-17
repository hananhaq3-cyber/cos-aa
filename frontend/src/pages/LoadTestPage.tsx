/**
 * Load Testing page — runs concurrent fetch() calls against the API
 * and displays timing metrics (latency, throughput, error rate).
 */
import { useState, useRef } from "react";
import { Zap, Play, BarChart3, Loader2 } from "lucide-react";
import api from "../api/client";
import clsx from "clsx";

interface TestResult {
  endpoint: string;
  concurrency: number;
  totalRequests: number;
  successCount: number;
  errorCount: number;
  avgLatencyMs: number;
  minLatencyMs: number;
  maxLatencyMs: number;
  p95LatencyMs: number;
  requestsPerSecond: number;
  totalDurationMs: number;
}

const ENDPOINTS = [
  { label: "Health Check", path: "/observability/health" },
  { label: "Dashboard Stats", path: "/dashboard/stats" },
  { label: "Agent List", path: "/agents" },
  { label: "Memory Stats", path: "/memory/stats" },
];

const CONCURRENCY_OPTIONS = [1, 5, 10, 25, 50];

export default function LoadTestPage() {
  const [selectedEndpoint, setSelectedEndpoint] = useState(ENDPOINTS[0].path);
  const [concurrency, setConcurrency] = useState(10);
  const [totalRequests, setTotalRequests] = useState(50);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<TestResult[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const runTest = async () => {
    setRunning(true);
    setProgress(0);
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;

    const latencies: number[] = [];
    let successCount = 0;
    let errorCount = 0;
    let completed = 0;

    const startTime = performance.now();

    const worker = async () => {
      while (completed < totalRequests && !signal.aborted) {
        const reqStart = performance.now();
        try {
          await api.get(selectedEndpoint, { signal });
          successCount++;
        } catch {
          if (signal.aborted) return;
          errorCount++;
        }
        const elapsed = performance.now() - reqStart;
        latencies.push(elapsed);
        completed++;
        setProgress(completed);
      }
    };

    // Launch concurrent workers
    const workers = Array.from(
      { length: Math.min(concurrency, totalRequests) },
      () => worker()
    );
    await Promise.all(workers);

    const totalDuration = performance.now() - startTime;

    if (signal.aborted) {
      setRunning(false);
      return;
    }

    // Calculate metrics
    latencies.sort((a, b) => a - b);
    const avg = latencies.reduce((sum, l) => sum + l, 0) / (latencies.length || 1);
    const p95Index = Math.floor(latencies.length * 0.95);

    const result: TestResult = {
      endpoint: ENDPOINTS.find((e) => e.path === selectedEndpoint)?.label || selectedEndpoint,
      concurrency,
      totalRequests: completed,
      successCount,
      errorCount,
      avgLatencyMs: Math.round(avg),
      minLatencyMs: Math.round(latencies[0] ?? 0),
      maxLatencyMs: Math.round(latencies[latencies.length - 1] ?? 0),
      p95LatencyMs: Math.round(latencies[p95Index] ?? 0),
      requestsPerSecond: Math.round((completed / totalDuration) * 1000 * 100) / 100,
      totalDurationMs: Math.round(totalDuration),
    };

    setResults((prev) => [result, ...prev]);
    setRunning(false);
  };

  const stopTest = () => {
    abortRef.current?.abort();
    setRunning(false);
  };

  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Zap size={20} className="text-yellow-400" />
          Load Testing
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Run concurrent requests against API endpoints to measure performance.
        </p>
      </div>

      {/* Config */}
      <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl mb-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Endpoint */}
          <div>
            <label className="text-xs text-gray-400 block mb-1.5">Endpoint</label>
            <select
              value={selectedEndpoint}
              onChange={(e) => setSelectedEndpoint(e.target.value)}
              disabled={running}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-primary-500"
            >
              {ENDPOINTS.map((ep) => (
                <option key={ep.path} value={ep.path}>
                  {ep.label}
                </option>
              ))}
            </select>
          </div>

          {/* Concurrency */}
          <div>
            <label className="text-xs text-gray-400 block mb-1.5">Concurrency</label>
            <div className="flex gap-1">
              {CONCURRENCY_OPTIONS.map((c) => (
                <button
                  key={c}
                  onClick={() => setConcurrency(c)}
                  disabled={running}
                  className={clsx(
                    "flex-1 py-2 text-xs rounded-lg transition-colors",
                    concurrency === c
                      ? "bg-primary-600/20 text-primary-400 border border-primary-500/30"
                      : "bg-gray-950 border border-gray-700 text-gray-400 hover:border-gray-600"
                  )}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Total Requests */}
          <div>
            <label className="text-xs text-gray-400 block mb-1.5">Total Requests</label>
            <input
              type="number"
              value={totalRequests}
              onChange={(e) => setTotalRequests(Math.max(1, Math.min(200, Number(e.target.value))))}
              disabled={running}
              min={1}
              max={200}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-primary-500"
            />
          </div>
        </div>

        {/* Run/Stop buttons */}
        <div className="flex items-center gap-3">
          {!running ? (
            <button
              onClick={runTest}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 rounded-lg text-sm transition-colors"
            >
              <Play size={16} /> Run Test
            </button>
          ) : (
            <button
              onClick={stopTest}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm transition-colors"
            >
              Stop
            </button>
          )}
          {running && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 size={16} className="animate-spin" />
              <span>{progress}/{totalRequests}</span>
              <div className="w-32 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full transition-all"
                  style={{ width: `${(progress / totalRequests) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-medium flex items-center gap-2">
            <BarChart3 size={16} className="text-gray-400" />
            Results ({results.length})
          </h2>

          {results.map((r, i) => (
            <div
              key={i}
              className="p-4 bg-gray-900 border border-gray-800 rounded-xl"
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-gray-200">
                  {r.endpoint}
                </h3>
                <span className="text-xs text-gray-500">
                  {r.concurrency} concurrent | {r.totalRequests} total | {r.totalDurationMs}ms
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Metric label="Avg Latency" value={`${r.avgLatencyMs}ms`} />
                <Metric label="P95 Latency" value={`${r.p95LatencyMs}ms`} />
                <Metric label="Min / Max" value={`${r.minLatencyMs} / ${r.maxLatencyMs}ms`} />
                <Metric label="Req/sec" value={`${r.requestsPerSecond}`} highlight />
                <Metric label="Success" value={`${r.successCount}`} good />
                <Metric label="Errors" value={`${r.errorCount}`} bad={r.errorCount > 0} />
                <Metric
                  label="Error Rate"
                  value={`${((r.errorCount / r.totalRequests) * 100).toFixed(1)}%`}
                  bad={r.errorCount > 0}
                />
                <Metric
                  label="Throughput"
                  value={`${((r.successCount / r.totalDurationMs) * 1000).toFixed(1)} req/s`}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  highlight,
  good,
  bad,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  good?: boolean;
  bad?: boolean;
}) {
  return (
    <div className="bg-gray-950 rounded-lg px-3 py-2">
      <p className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</p>
      <p
        className={clsx(
          "text-sm font-medium mt-0.5",
          highlight
            ? "text-primary-400"
            : good
              ? "text-green-400"
              : bad
                ? "text-red-400"
                : "text-gray-200"
        )}
      >
        {value}
      </p>
    </div>
  );
}
