import { useMemo, useState } from "react";
import type { StepEvent } from "../../types";

interface Props {
  /** All steps — viewer extracts the ones with screenshot_path. */
  steps: StepEvent[];
  /** Whether the run is still active. */
  isRunning: boolean;
}

/**
 * Browser-chrome styled screenshot viewer. Displays the latest screenshot
 * from the agent's browser session, with navigation between all captured
 * screenshots and a mock address bar.
 */
export default function ScreenshotViewer({ steps, isRunning }: Props) {
  const screenshotSteps = useMemo(
    () => steps.filter((s) => s.screenshot_path),
    [steps],
  );

  const [viewIndex, setViewIndex] = useState<number | null>(null);

  // Default to the latest screenshot
  const currentIndex = viewIndex ?? screenshotSteps.length - 1;
  const current = screenshotSteps[currentIndex] ?? null;

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < screenshotSteps.length - 1;

  if (screenshotSteps.length === 0) {
    return (
      <div className="rounded-xl border border-surface-700 bg-surface-800 overflow-hidden">
        <div className="flex items-center gap-2 border-b border-surface-700 px-4 py-2.5">
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-danger/60" />
            <span className="h-2 w-2 rounded-full bg-warning/60" />
            <span className="h-2 w-2 rounded-full bg-success/60" />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
            Browser View
          </span>
        </div>
        <div className="flex items-center justify-center py-12 text-xs text-text-muted">
          {isRunning
            ? "Screenshots will appear when the agent captures the browser..."
            : "No screenshots captured during this run."}
        </div>
      </div>
    );
  }

  // Build a display URL from the screenshot path or tool name
  const displayUrl = current?.screenshot_path
    ? current.screenshot_path.split("/").pop() ?? "screenshot.png"
    : "screenshot.png";

  return (
    <div className="rounded-xl border border-surface-700 bg-surface-800 overflow-hidden">
      {/* Chrome title bar */}
      <div className="flex items-center gap-2 border-b border-surface-700 bg-surface-800 px-4 py-2">
        {/* Traffic lights */}
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-danger/60" />
          <span className="h-2 w-2 rounded-full bg-warning/60" />
          <span className="h-2 w-2 rounded-full bg-success/60" />
        </div>

        {/* Address bar */}
        <div className="flex flex-1 items-center gap-1.5 rounded-md bg-surface-900 px-3 py-1">
          <svg
            className="h-3 w-3 shrink-0 text-text-muted"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4"
            />
          </svg>
          <span className="truncate font-mono text-[10px] text-text-muted">
            {displayUrl}
          </span>
        </div>

        {/* Step badge */}
        <span className="shrink-0 rounded-full bg-surface-700 px-2 py-0.5 text-[10px] font-bold text-text-muted">
          Step #{current?.step_index}
        </span>
      </div>

      {/* Screenshot viewport */}
      <div className="relative bg-surface-900">
        <img
          src={`/api/screenshots/${encodeURIComponent(current?.screenshot_path ?? "")}`}
          alt={`Screenshot from step ${current?.step_index}`}
          className="w-full object-contain"
          style={{ maxHeight: "360px" }}
          onError={(e) => {
            // Replace broken images with a placeholder
            const target = e.currentTarget;
            target.style.display = "none";
            target.parentElement?.classList.add("screenshot-error");
          }}
        />
        {/* Fallback for failed loads */}
        <div className="screenshot-fallback hidden items-center justify-center py-16 text-xs text-text-muted">
          Screenshot could not be loaded
        </div>
      </div>

      {/* Navigation footer */}
      {screenshotSteps.length > 1 && (
        <div className="flex items-center justify-between border-t border-surface-700 px-4 py-2">
          <button
            onClick={() => setViewIndex(Math.max(0, currentIndex - 1))}
            disabled={!hasPrev}
            className="rounded-md px-2 py-1 text-[10px] font-medium text-text-secondary hover:bg-surface-700 hover:text-text-primary disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            Prev
          </button>
          <span className="font-mono text-[10px] text-text-muted">
            {currentIndex + 1} / {screenshotSteps.length}
          </span>
          <button
            onClick={() =>
              setViewIndex(
                Math.min(screenshotSteps.length - 1, currentIndex + 1),
              )
            }
            disabled={!hasNext}
            className="rounded-md px-2 py-1 text-[10px] font-medium text-text-secondary hover:bg-surface-700 hover:text-text-primary disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
