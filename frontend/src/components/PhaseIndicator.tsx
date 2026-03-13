/**
 * OODA Phase indicator — shows the current phase with animated progress.
 */
import clsx from "clsx";

const PHASES = ["OBSERVING", "ORIENTING", "DECIDING", "ACTING", "REVIEWING"];

interface PhaseIndicatorProps {
  currentPhase: string;
}

export default function PhaseIndicator({ currentPhase }: PhaseIndicatorProps) {
  const activeIdx = PHASES.indexOf(currentPhase);

  return (
    <div className="flex items-center justify-center gap-1 py-3">
      {PHASES.map((phase, idx) => (
        <div key={phase} className="flex items-center">
          <div
            className={clsx(
              "flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium transition-all duration-300",
              idx < activeIdx && "bg-green-600 text-white",
              idx === activeIdx &&
                "bg-primary-500 text-white animate-pulse-slow ring-2 ring-primary-400/50",
              idx > activeIdx && "bg-gray-800 text-gray-500"
            )}
          >
            {phase[0]}
          </div>
          {idx < PHASES.length - 1 && (
            <div
              className={clsx(
                "w-6 h-0.5 mx-0.5",
                idx < activeIdx ? "bg-green-600" : "bg-gray-800"
              )}
            />
          )}
        </div>
      ))}
      <span className="ml-3 text-xs text-gray-400">{currentPhase}</span>
    </div>
  );
}
