/**
 * Memory explorer — search across semantic and episodic memory.
 */
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { searchMemory } from "../api/endpoints";
import MemoryCard from "../components/MemoryCard";
import type { MemorySearchResponse } from "../types";

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemorySearchResponse | null>(null);

  const searchMutation = useMutation({
    mutationFn: (q: string) => searchMemory(q, 10),
    onSuccess: (data) => setResults(data),
  });

  const handleSearch = () => {
    const text = query.trim();
    if (!text) return;
    searchMutation.mutate(text);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold mb-1">Memory Explorer</h1>
        <p className="text-sm text-gray-500">
          Search across semantic and episodic memory tiers.
        </p>
      </div>

      {/* Search bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        className="flex gap-3 mb-6"
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search memory..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500"
        />
        <button
          type="submit"
          disabled={searchMutation.isPending}
          className="p-3 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 rounded-xl transition-colors"
        >
          <Search size={18} />
        </button>
      </form>

      {/* Results meta */}
      {results && (
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-400">
            {results.total} results for &quot;{results.query}&quot;
          </p>
          <p className="text-xs text-gray-500">
            {results.retrieval_latency_ms.toFixed(1)}ms
          </p>
        </div>
      )}

      {/* Results */}
      <div className="space-y-3">
        {searchMutation.isPending && (
          <p className="text-center py-8 text-gray-500 text-sm">
            Searching...
          </p>
        )}
        {results?.results.map((frag) => (
          <MemoryCard key={frag.fragment_id} fragment={frag} />
        ))}
        {results && results.results.length === 0 && (
          <p className="text-center py-8 text-gray-500 text-sm">
            No memories found matching your query.
          </p>
        )}
      </div>
    </div>
  );
}
