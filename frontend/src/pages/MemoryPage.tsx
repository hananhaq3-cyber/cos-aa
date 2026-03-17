/**
 * Memory explorer — browse, create, delete, and search memory.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Plus, Database, Download } from "lucide-react";
import {
  searchMemory,
  listMemory,
  storeMemory,
  deleteMemory,
  getMemoryStats,
  exportMemory,
} from "../api/endpoints";
import MemoryCard from "../components/MemoryCard";
import clsx from "clsx";
import type { MemorySearchResponse } from "../types";

type Tab = "browse" | "search";

export default function MemoryPage() {
  const [tab, setTab] = useState<Tab>("browse");
  const [exporting, setExporting] = useState(false);

  const statsQuery = useQuery({
    queryKey: ["memory-stats"],
    queryFn: getMemoryStats,
  });

  const handleExportAll = async () => {
    setExporting(true);
    try {
      await exportMemory("json");
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold mb-1">Memory Explorer</h1>
          <p className="text-sm text-gray-500">
            Browse, create, and search across memory tiers.
          </p>
        </div>
        <button
          onClick={handleExportAll}
          disabled={exporting}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-700 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Export all memories as JSON"
        >
          <Download size={16} />
          Export All
        </button>
      </div>

      {/* Stats bar */}
      {statsQuery.data && (
        <div className="flex flex-wrap gap-3 mb-6">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 border border-gray-800 rounded-lg">
            <Database size={14} className="text-gray-400" />
            <span className="text-xs text-gray-400">
              Total: {statsQuery.data.total}
            </span>
          </div>
          {Object.entries(statsQuery.data.by_tier).map(([tier, count]) => (
            <div
              key={tier}
              className="px-3 py-1.5 bg-gray-900 border border-gray-800 rounded-lg"
            >
              <span className="text-xs text-gray-400">
                {tier}: {count}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-800">
        <button
          onClick={() => setTab("browse")}
          className={clsx(
            "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
            tab === "browse"
              ? "border-primary-500 text-primary-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          )}
        >
          Browse
        </button>
        <button
          onClick={() => setTab("search")}
          className={clsx(
            "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
            tab === "search"
              ? "border-primary-500 text-primary-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          )}
        >
          Search
        </button>
      </div>

      {tab === "browse" && <BrowseTab />}
      {tab === "search" && <SearchTab />}
    </div>
  );
}

/* ── Browse Tab ── */

function BrowseTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [filterType, setFilterType] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const memoriesQuery = useQuery({
    queryKey: ["memories", filterType],
    queryFn: () => listMemory(50, 0, filterType || undefined),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
      setDeletingId(null);
    },
    onError: () => setDeletingId(null),
  });

  const handleDelete = (id: string) => {
    setDeletingId(id);
    deleteMutation.mutate(id);
  };

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-primary-500"
        >
          <option value="">All types</option>
          <option value="manual">Manual</option>
          <option value="observation">Observation</option>
          <option value="decision">Decision</option>
          <option value="action">Action</option>
          <option value="reflection">Reflection</option>
        </select>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-500 rounded-lg text-sm transition-colors"
        >
          <Plus size={16} />
          Store Memory
        </button>
      </div>

      {/* Create form */}
      {showForm && <StoreMemoryForm onDone={() => setShowForm(false)} />}

      {/* List */}
      <div className="space-y-3">
        {memoriesQuery.isLoading && (
          <p className="text-center py-8 text-gray-500 text-sm">Loading...</p>
        )}
        {memoriesQuery.data?.memories.map((frag) => (
          <MemoryCard
            key={frag.fragment_id}
            fragment={frag}
            onDelete={handleDelete}
            deleting={deletingId === frag.fragment_id}
          />
        ))}
        {memoriesQuery.data && memoriesQuery.data.memories.length === 0 && (
          <p className="text-center py-8 text-gray-500 text-sm">
            No memories yet. Store one to get started.
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Store Memory Form ── */

function StoreMemoryForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [content, setContent] = useState("");
  const [eventType, setEventType] = useState("manual");
  const [tagsInput, setTagsInput] = useState("");
  const [importance, setImportance] = useState(0.5);

  const mutation = useMutation({
    mutationFn: storeMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
      setContent("");
      setTagsInput("");
      setImportance(0.5);
      onDone();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    mutation.mutate({
      content: content.trim(),
      event_type: eventType,
      tags,
      importance_score: importance,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-3"
    >
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Memory content..."
        rows={3}
        className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500 resize-none"
      />
      <div className="flex flex-col sm:flex-row gap-3">
        <select
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
          className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-primary-500"
        >
          <option value="manual">Manual</option>
          <option value="observation">Observation</option>
          <option value="decision">Decision</option>
          <option value="action">Action</option>
          <option value="reflection">Reflection</option>
        </select>
        <input
          type="text"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="Tags (comma-separated)"
          className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500"
        />
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400">Importance:</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={importance}
            onChange={(e) => setImportance(parseFloat(e.target.value))}
            className="w-20"
          />
          <span className="text-xs text-gray-400 w-6">{importance}</span>
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={mutation.isPending || !content.trim()}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 rounded-lg text-sm transition-colors"
        >
          {mutation.isPending ? "Storing..." : "Store"}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors"
        >
          Cancel
        </button>
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-400">
          Failed to store memory. Please try again.
        </p>
      )}
    </form>
  );
}

/* ── Search Tab ── */

function SearchTab() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemorySearchResponse | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedEventTypes, setSelectedEventTypes] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<"relevance" | "date">("relevance");

  const searchMutation = useMutation({
    mutationFn: (searchParams: {
      query: string;
      tags?: string[];
      event_types?: string[];
      created_after?: string;
      created_before?: string;
      sort_by?: string;
    }) =>
      searchMemory(
        searchParams.query,
        10,
        ["semantic", "episodic"],
        searchParams.tags || []
      ),
    onSuccess: (data) => setResults(data),
  });

  const handleSearch = () => {
    const text = query.trim();
    if (!text) return;
    searchMutation.mutate({
      query: text,
      tags: selectedTags,
      event_types: selectedEventTypes,
      created_after: dateFrom,
      created_before: dateTo,
      sort_by: sortBy,
    });
  };

  const hasActiveFilters = dateFrom || dateTo || selectedTags.length > 0 || selectedEventTypes.length > 0 || sortBy !== "relevance";

  return (
    <div>
      {/* Search bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        className="flex gap-3 mb-4"
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
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors"
        >
          Filters {hasActiveFilters && <span className="ml-1 text-xs text-primary-400">●</span>}
        </button>
      </form>

      {/* Filter Panel */}
      {showFilters && (
        <div className="mb-4 p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
          {/* Date Range */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-400">Date Range</label>
            <div className="flex gap-2">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-primary-500"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>

          {/* Event Types */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-400">Event Types</label>
            <div className="flex flex-wrap gap-2">
              {["manual", "observation", "decision", "action", "reflection"].map((type) => (
                <button
                  key={type}
                  onClick={() =>
                    setSelectedEventTypes((prev) =>
                      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
                    )
                  }
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    selectedEventTypes.includes(type)
                      ? "bg-primary-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Sort */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-400">Sort By</label>
            <div className="flex gap-2">
              {["relevance", "date"].map((option) => (
                <button
                  key={option}
                  onClick={() => setSortBy(option as "relevance" | "date")}
                  className={`px-3 py-1 text-xs rounded transition-colors ${
                    sortBy === option
                      ? "bg-primary-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={() => {
                setDateFrom("");
                setDateTo("");
                setSelectedTags([]);
                setSelectedEventTypes([]);
                setSortBy("relevance");
                setResults(null);
              }}
              className="w-full px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs transition-colors"
            >
              Clear All Filters
            </button>
          )}
        </div>
      )}

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
            No memories found matching your filters.
          </p>
        )}
      </div>
    </div>
  );
}
