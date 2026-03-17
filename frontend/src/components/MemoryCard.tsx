/**
 * Memory fragment card for search results and browse list.
 */
import clsx from "clsx";
import { Trash2 } from "lucide-react";
import type { MemoryFragment } from "../types";

interface MemoryCardProps {
  fragment: MemoryFragment;
  onDelete?: (id: string) => void;
  deleting?: boolean;
}

const tierColors: Record<string, string> = {
  SEMANTIC: "border-purple-500/40 bg-purple-500/5",
  EPISODIC: "border-blue-500/40 bg-blue-500/5",
  PROCEDURAL: "border-green-500/40 bg-green-500/5",
  WORKING: "border-yellow-500/40 bg-yellow-500/5",
  manual: "border-cyan-500/40 bg-cyan-500/5",
};

export default function MemoryCard({ fragment, onDelete, deleting }: MemoryCardProps) {
  const borderClass =
    tierColors[fragment.tier] || "border-gray-700 bg-gray-900";

  return (
    <div
      className={clsx(
        "rounded-xl border p-4 transition-colors hover:border-gray-600",
        borderClass
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          {fragment.tier}
        </span>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            score: {fragment.relevance_score.toFixed(3)}
          </span>
          {onDelete && (
            <button
              onClick={() => onDelete(fragment.fragment_id)}
              disabled={deleting}
              className="p-1 text-gray-500 hover:text-red-400 disabled:opacity-50 transition-colors"
              title="Delete memory"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-200 leading-relaxed mb-2">
        {fragment.content.length > 300
          ? fragment.content.slice(0, 300) + "..."
          : fragment.content}
      </p>
      {fragment.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {fragment.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
      {fragment.created_at && (
        <p className="text-xs text-gray-500 mt-2">
          {new Date(fragment.created_at).toLocaleString()}
        </p>
      )}
      {fragment.summary && (
        <p className="text-xs text-gray-500 mt-1 italic">{fragment.summary}</p>
      )}
    </div>
  );
}
