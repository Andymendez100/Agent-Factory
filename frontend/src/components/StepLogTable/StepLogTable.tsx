import { useEffect, useRef } from "react";
import type { StepEvent } from "../../types";

interface Props {
  steps: StepEvent[];
  isRunning: boolean;
  /** Called when user clicks a step row (e.g. to show detail). */
  onSelectStep?: (step: StepEvent) => void;
  /** Currently selected step index, if any. */
  selectedIndex?: number;
}

const TOOL_ICONS: Record<string, string> = {
  login: "\u{1F511}",
  navigate: "\u{1F310}",
  scrape: "\u{1F4CB}",
  click: "\u{1F5B1}",
  fill: "\u{270F}",
  screenshot: "\u{1F4F7}",
  analyze: "\u{1F4CA}",
  export: "\u{1F4BE}",
  alert: "\u{1F514}",
};

function getToolIcon(toolName: string | null): string {
  if (!toolName) return "";
  const lower = toolName.toLowerCase();
  for (const [key, icon] of Object.entries(TOOL_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return "\u{2699}";
}

function summarizeInput(step: StepEvent): string {
  if (step.step_type === "agent_thinking") {
    return step.agent_reasoning?.slice(0, 100) ?? "--";
  }
  if (!step.tool_input) return "--";
  return JSON.stringify(step.tool_input).slice(0, 100);
}

function summarizeOutput(step: StepEvent): string {
  if (step.step_type === "agent_thinking") return "--";
  if (!step.tool_output) return "--";
  const str = JSON.stringify(step.tool_output);
  return str.length > 80 ? str.slice(0, 80) + "..." : str;
}

/**
 * Step log table with all columns: index, type, tool/action, input summary,
 * output summary, duration, and optional screenshot indicator.
 */
export default function StepLogTable({
  steps,
  isRunning,
  onSelectStep,
  selectedIndex,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest step
  useEffect(() => {
    if (isRunning && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [steps.length, isRunning]);

  return (
    <div className="rounded-xl border border-surface-700 bg-surface-800 overflow-hidden">
      <div className="flex items-center justify-between border-b border-surface-700 px-5 py-3">
        <h2 className="text-xs font-medium uppercase tracking-wider text-text-muted">
          Step Log
        </h2>
        <span className="font-mono text-[10px] text-text-muted">
          {steps.length} step{steps.length !== 1 && "s"}
        </span>
      </div>

      {steps.length === 0 ? (
        <div className="px-5 py-10 text-center">
          {isRunning ? (
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center gap-1">
                <span
                  className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent-500"
                  style={{ animationDelay: "0ms" }}
                />
                <span
                  className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent-500"
                  style={{ animationDelay: "150ms" }}
                />
                <span
                  className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-accent-500"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
              <p className="text-xs text-text-muted">
                Steps will appear as the agent works...
              </p>
            </div>
          ) : (
            <p className="text-xs text-text-muted">No steps recorded.</p>
          )}
        </div>
      ) : (
        <div className="max-h-[320px] overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10 bg-surface-800">
              <tr className="border-b border-surface-700 text-left">
                <th className="w-10 px-4 py-2.5 font-medium text-text-muted">
                  #
                </th>
                <th className="w-16 px-4 py-2.5 font-medium text-text-muted">
                  Type
                </th>
                <th className="w-32 px-4 py-2.5 font-medium text-text-muted">
                  Tool / Action
                </th>
                <th className="px-4 py-2.5 font-medium text-text-muted">
                  Input
                </th>
                <th className="px-4 py-2.5 font-medium text-text-muted">
                  Output
                </th>
                <th className="w-16 px-4 py-2.5 text-right font-medium text-text-muted">
                  Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700/40">
              {steps.map((s, i) => {
                const isSelected = selectedIndex === s.step_index;
                const isLatest = i === steps.length - 1 && isRunning;
                return (
                  <tr
                    key={s.step_index}
                    onClick={() => onSelectStep?.(s)}
                    className={`
                      transition-colors
                      ${onSelectStep ? "cursor-pointer" : ""}
                      ${isSelected ? "bg-accent-500/10" : "hover:bg-surface-700/30"}
                      ${isLatest ? "bg-surface-700/20" : ""}
                    `}
                  >
                    <td className="px-4 py-2.5 font-mono text-text-muted">
                      {s.step_index}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                          s.step_type === "agent_thinking"
                            ? "bg-accent-500/15 text-accent-400"
                            : "bg-success/15 text-success"
                        }`}
                      >
                        {s.step_type === "agent_thinking"
                          ? "THINK"
                          : "TOOL"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="flex items-center gap-1.5 font-medium text-text-primary">
                        {s.step_type === "tool_call" && (
                          <span className="text-xs">{getToolIcon(s.tool_name)}</span>
                        )}
                        {s.step_type === "agent_thinking"
                          ? "Agent"
                          : s.tool_name ?? "--"}
                      </span>
                      {s.screenshot_path && (
                        <span className="mt-0.5 inline-flex items-center gap-0.5 text-[9px] text-text-muted">
                          {"\u{1F4F7}"} screenshot
                        </span>
                      )}
                    </td>
                    <td className="max-w-[200px] truncate px-4 py-2.5 text-text-secondary">
                      {summarizeInput(s)}
                    </td>
                    <td className="max-w-[180px] truncate px-4 py-2.5 text-text-secondary">
                      {summarizeOutput(s)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-text-muted">
                      {s.duration_ms > 0
                        ? `${(s.duration_ms / 1000).toFixed(1)}s`
                        : isLatest
                          ? "\u{22EF}"
                          : "--"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
